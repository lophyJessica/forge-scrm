"""选题库路由（模块 02）：批量生成 / 生成历史 / 人工筛选 / CRUD。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.models.user import User
from app.core.deps import CurrentUser, DbSession, require_permission
from app.core.enums import Permission, ScreeningResult, Specialty, TopicStatus
from app.core.exceptions import BizError, not_found
from app.core.logging import get_logger
from app.models.topic import Topic
from app.schemas.common import OkResult, PageResult
from app.schemas.topic import (
    TopicBatchOut,
    TopicCreate,
    TopicGenerateRequest,
    TopicGenerateResult,
    TopicOut,
    TopicScreenRequest,
    TopicUpdate,
)
from app.services import deepseek_service as ds
from app.services import topic_service as svc

logger = get_logger(__name__)
router = APIRouter(prefix="/api/topics", tags=["选题库"])


@router.post("/generate", response_model=TopicGenerateResult, summary="批量生成选题（R4：每方向10条，跨批次完全重复去重）")
def generate_topics(
    payload: TopicGenerateRequest,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.选题生成)),
) -> TopicGenerateResult:
    system_prompt, user_prompt, snapshot, _materials = svc.build_prompt(
        db,
        payload.direction,
        payload.specialty,
        payload.count,
        payload.material_ids,
        payload.prompt_template_id,
    )

    try:
        items, raw = ds.chat_json(
            system_prompt, user_prompt, validator=svc.validate_topics_payload(payload.count)
        )
    except ds.DeepSeekError as exc:
        # 失败留痕：原始响应仍然留档，便于重试与追溯（S03/S04）
        archive = ds.archive_raw(exc.raw, "topic_generate_failed")
        logger.error("选题生成失败，原始响应已留档：%s", archive)
        raise BizError(f"选题生成失败，可重试。原始响应留档：{archive}；原因：{exc.message}")

    archive = ds.archive_raw(raw, "topic_generate")
    batch_no = svc.new_batch_no()

    seen = svc.existing_title_keys(db)  # 跨批次
    saved: list[Topic] = []
    deduped = 0
    for item in items:
        key = svc.normalize_title(item["title"])
        if key in seen:  # 同批次内 + 跨批次完全重复去重（R14）
            deduped += 1
            continue
        seen.add(key)
        topic = Topic(
            title=item["title"],
            direction=payload.direction,
            specialty=payload.specialty,
            customer_scenario=item["customer_scenario"],
            user_perspective=item["user_perspective"],
            business_direction=item["business_direction"],
            core_angle=item["core_angle"],
            topic_principle=item["topic_principle"],
            topic_angle=item["topic_angle"],
            status=TopicStatus.待筛选,
            batch_no=batch_no,
            prompt_version_snapshot=snapshot,
            ai_raw_response=raw,
            created_by=current_user.id,
        )
        db.add(topic)
        db.flush()
        if payload.material_ids:
            svc.set_topic_materials(db, topic, payload.material_ids)
        saved.append(topic)

    db.commit()
    for t in saved:
        db.refresh(t)
    logger.info("选题生成：batch=%s 返回%s条 去重%s条 入库%s条", batch_no, len(items), deduped, len(saved))
    return TopicGenerateResult(
        batch_no=batch_no,
        requested=payload.count,
        generated=len(items),
        deduped=deduped,
        saved=len(saved),
        topics=[svc.to_out(db, t) for t in saved],
        ai_raw_archive=archive,
    )


@router.get("/batches", response_model=list[TopicBatchOut], summary="生成历史批次（M12：每次生成留痕）")
def list_batches(_: CurrentUser, db: DbSession) -> list[TopicBatchOut]:
    stmt = (
        select(
            Topic.batch_no,
            Topic.direction,
            func.count(Topic.id).label("count"),
            func.min(Topic.created_at).label("created_at"),
            func.min(Topic.created_by).label("created_by"),
        )
        .where(Topic.batch_no.is_not(None))
        .group_by(Topic.batch_no, Topic.direction)
        .order_by(func.min(Topic.created_at).desc())
    )
    return [
        TopicBatchOut(
            batch_no=r.batch_no,
            direction=r.direction,
            count=r.count,
            created_at=r.created_at,
            created_by=r.created_by,
        )
        for r in db.execute(stmt).all()
    ]


@router.get("", response_model=PageResult[TopicOut], summary="选题列表")
def list_topics(
    _: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: TopicStatus | None = None,
    direction: str | None = None,
    specialty: Specialty | None = None,
    batch_no: str | None = None,
    keyword: str | None = None,
) -> PageResult[TopicOut]:
    stmt = select(Topic)
    if status is not None:
        stmt = stmt.where(Topic.status == status)
    if direction:
        stmt = stmt.where(Topic.direction == direction)
    if specialty is not None:
        stmt = stmt.where(Topic.specialty == specialty)
    if batch_no:
        stmt = stmt.where(Topic.batch_no == batch_no)
    if keyword:
        stmt = stmt.where(Topic.title.like(f"%{keyword}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Topic.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PageResult[TopicOut](
        total=total, page=page, page_size=page_size, items=[svc.to_out(db, r) for r in rows]
    )


@router.post("", response_model=TopicOut, summary="手动创建独立选题（M15）")
def create_topic(
    payload: TopicCreate,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.选题手动新增)),
) -> TopicOut:
    topic = Topic(
        **payload.model_dump(exclude={"material_ids"}),
        status=TopicStatus.待筛选,
        batch_no=None,
        ai_raw_response=None,  # 独立创建无 DeepSeek 调用，可为空
        created_by=current_user.id,
    )
    db.add(topic)
    db.flush()
    if payload.material_ids:
        svc.set_topic_materials(db, topic, payload.material_ids)
    db.commit()
    db.refresh(topic)
    return svc.to_out(db, topic)


@router.get("/{topic_id}", response_model=TopicOut, summary="选题详情")
def get_topic(topic_id: int, _: CurrentUser, db: DbSession) -> TopicOut:
    topic = db.get(Topic, topic_id)
    if not topic:
        raise not_found("选题")
    return svc.to_out(db, topic)


@router.get("/{topic_id}/ai-raw", summary="查看该选题的 AI 原始响应留档（S04）")
def get_topic_ai_raw(topic_id: int, _: CurrentUser, db: DbSession) -> dict:
    topic = db.get(Topic, topic_id)
    if not topic:
        raise not_found("选题")
    return {
        "topic_id": topic.id,
        "batch_no": topic.batch_no,
        "ai_raw_response": topic.ai_raw_response,
        "prompt_version_snapshot": topic.prompt_version_snapshot,
    }


@router.put("/{topic_id}", response_model=TopicOut, summary="人工修改选题（D8：不生成版本历史）")
def update_topic(
    topic_id: int,
    payload: TopicUpdate,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.选题修改)),
) -> TopicOut:
    topic = db.get(Topic, topic_id)
    if not topic:
        raise not_found("选题")
    data = payload.model_dump(exclude_unset=True, exclude={"material_ids"})
    for k, v in data.items():
        setattr(topic, k, v)
    if payload.material_ids is not None:
        svc.set_topic_materials(db, topic, payload.material_ids)
    db.commit()
    db.refresh(topic)
    return svc.to_out(db, topic)


@router.post("/{topic_id}/screen", response_model=TopicOut, summary="人工筛选（R3：必须筛选后才能使用）")
def screen_topic(
    topic_id: int, payload: TopicScreenRequest, current_user: CurrentUser, db: DbSession
) -> TopicOut:
    topic = db.get(Topic, topic_id)
    if not topic:
        raise not_found("选题")
    if topic.status != TopicStatus.待筛选:
        raise BizError(f"当前状态「{topic.status.value}」不可筛选")
    topic.screening_result = payload.screening_result
    topic.status = (
        TopicStatus.已选定
        if payload.screening_result == ScreeningResult.选中
        else TopicStatus.已废弃
    )
    db.commit()
    db.refresh(topic)
    return svc.to_out(db, topic)


@router.post("/{topic_id}/discard", response_model=TopicOut, summary="废弃选题")
def discard_topic(topic_id: int, _: CurrentUser, db: DbSession) -> TopicOut:
    topic = db.get(Topic, topic_id)
    if not topic:
        raise not_found("选题")
    if topic.status in (TopicStatus.已废弃, TopicStatus.已使用):
        raise BizError(f"当前状态「{topic.status.value}」不可废弃")
    topic.status = TopicStatus.已废弃
    db.commit()
    db.refresh(topic)
    return svc.to_out(db, topic)


@router.delete("/{topic_id}", response_model=OkResult, summary="删除选题（仅管理员）")
def delete_topic(
    topic_id: int,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.选题修改)),
) -> OkResult:
    topic = db.get(Topic, topic_id)
    if not topic:
        raise not_found("选题")
    db.delete(topic)
    db.commit()
    return OkResult(message="选题已删除")
