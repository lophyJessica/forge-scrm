"""脚本库路由（模块 03）：生成 / CRUD / 版本历史 / 对比 / 回退 / 审核 / 标记已使用。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.models.user import User
from app.core.deps import AdminUser, CurrentUser, DbSession, require_permission
from app.core.enums import Permission, ScriptStatus, ScriptStyle, TopicStatus
from app.core.exceptions import BizError, not_found
from app.core.logging import get_logger
from app.models.base import utcnow
from app.models.script import Script, ScriptVersion
from app.models.topic import Topic
from app.schemas.common import OkResult, PageResult
from app.schemas.script import (
    ScriptCreate,
    ScriptDiffOut,
    ScriptGenerateRequest,
    ScriptGenerateResult,
    ScriptOut,
    ScriptReview,
    ScriptRollbackRequest,
    ScriptUpdate,
    ScriptVersionOut,
)
from app.services import deepseek_service as ds
from app.services import script_service as svc

logger = get_logger(__name__)
router = APIRouter(prefix="/api/scripts", tags=["脚本库"])


@router.post("/generate", response_model=ScriptGenerateResult, summary="基于选题生成 2-3 版脚本（R5/R10）")
def generate_scripts(
    payload: ScriptGenerateRequest, current_user: CurrentUser, db: DbSession
) -> ScriptGenerateResult:
    topic = db.get(Topic, payload.topic_id)
    if not topic:
        raise not_found("选题")
    if topic.status not in (TopicStatus.已选定, TopicStatus.已生成脚本):
        raise BizError(f"选题必须先人工筛选为「已选定」才能生成脚本（R3），当前：{topic.status.value}")

    elements = [e.value for e in payload.content_elements]
    system_prompt, user_prompt, snapshot = svc.build_prompt(
        db,
        topic,
        payload.style,
        elements,
        payload.version_count,
        payload.material_ids,
        payload.prompt_template_id,
        payload.prompt_content,
    )

    try:
        contents, raw = ds.chat_json(
            system_prompt,
            user_prompt,
            validator=svc.validate_scripts_payload(payload.version_count),
        )
    except ds.DeepSeekError as exc:
        archive = ds.archive_raw(exc.raw, "script_generate_failed")
        logger.error("脚本生成失败，原始响应已留档：%s", archive)
        raise BizError(f"脚本生成失败，可重试。原始响应留档：{archive}；原因：{exc.message}")

    archive = ds.archive_raw(raw, "script_generate")
    saved: list[Script] = []
    for content in contents[: payload.version_count]:
        script = Script(
            topic_id=topic.id,
            content=content,
            style=payload.style,
            content_elements=elements,
            current_version=1,
            status=ScriptStatus.草稿,
            created_by=current_user.id,
            modified_by=current_user.id,
            material_refs=payload.material_ids or None,
            prompt_version_snapshot=snapshot,
        )
        db.add(script)
        db.flush()
        svc.add_version(db, script, content, current_user.id, note="AI 生成初版")
        saved.append(script)

    topic.status = TopicStatus.已生成脚本
    db.commit()
    for s in saved:
        db.refresh(s)
    return ScriptGenerateResult(
        topic_id=topic.id,
        generated=len(saved),
        scripts=[svc.to_out(db, s) for s in saved],
        ai_raw_archive=archive,
    )


@router.get("", response_model=PageResult[ScriptOut], summary="脚本列表")
def list_scripts(
    _: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: ScriptStatus | None = None,
    topic_id: int | None = None,
    style: ScriptStyle | None = None,
    keyword: str | None = None,
) -> PageResult[ScriptOut]:
    stmt = select(Script)
    if status is not None:
        stmt = stmt.where(Script.status == status)
    if topic_id is not None:
        stmt = stmt.where(Script.topic_id == topic_id)
    if style is not None:
        stmt = stmt.where(Script.style == style)
    if keyword:
        stmt = stmt.where(Script.content.like(f"%{keyword}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Script.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PageResult[ScriptOut](
        total=total, page=page, page_size=page_size, items=[svc.to_out(db, r) for r in rows]
    )


@router.post("", response_model=ScriptOut, summary="独立创建脚本（R9/R10：选题可为空，可后补关联）")
def create_script(payload: ScriptCreate, current_user: CurrentUser, db: DbSession) -> ScriptOut:
    if not payload.content or not payload.content.strip():
        raise BizError("脚本正文不能为空")
    if payload.topic_id is not None and not db.get(Topic, payload.topic_id):
        raise not_found("选题")

    script = Script(
        topic_id=payload.topic_id,
        content=payload.content,
        style=payload.style,
        content_elements=[e.value for e in payload.content_elements],
        current_version=1,
        status=ScriptStatus.草稿,
        created_by=current_user.id,
        modified_by=current_user.id,
        material_refs=payload.material_refs,
    )
    db.add(script)
    db.flush()
    svc.add_version(db, script, script.content, current_user.id, note="独立创建初版")
    db.commit()
    db.refresh(script)
    return svc.to_out(db, script)


@router.get("/{script_id}", response_model=ScriptOut, summary="脚本详情")
def get_script(script_id: int, _: CurrentUser, db: DbSession) -> ScriptOut:
    script = db.get(Script, script_id)
    if not script:
        raise not_found("脚本")
    return svc.to_out(db, script)


@router.put("/{script_id}", response_model=ScriptOut, summary="修改脚本（R11：版本号递增并保留历史）")
def update_script(
    script_id: int,
    payload: ScriptUpdate,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.脚本修改)),
) -> ScriptOut:
    script = db.get(Script, script_id)
    if not script:
        raise not_found("脚本")
    if script.status in (ScriptStatus.已废弃,):
        raise BizError("已废弃脚本不可修改")
    if payload.content is not None and not payload.content.strip():
        raise BizError("脚本正文不能为空")
    if payload.topic_id is not None:
        if not db.get(Topic, payload.topic_id):
            raise not_found("选题")
        script.topic_id = payload.topic_id
    if payload.style is not None:
        script.style = payload.style
    if payload.content_elements is not None:
        script.content_elements = [e.value for e in payload.content_elements]

    if payload.content is not None and payload.content != script.content:
        script.content = payload.content
        script.current_version += 1
        svc.add_version(db, script, payload.content, current_user.id, payload.note)
    script.modified_by = current_user.id
    script.modified_at = utcnow()
    db.commit()
    db.refresh(script)
    return svc.to_out(db, script)


@router.get("/{script_id}/versions", response_model=list[ScriptVersionOut], summary="版本历史")
def list_versions(
    script_id: int,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.脚本版本查看)),
) -> list[ScriptVersionOut]:
    if not db.get(Script, script_id):
        raise not_found("脚本")
    rows = db.scalars(
        select(ScriptVersion)
        .where(ScriptVersion.script_id == script_id)
        .order_by(ScriptVersion.version.desc(), ScriptVersion.id.desc())
    ).all()
    return [ScriptVersionOut.model_validate(r) for r in rows]


@router.get("/{script_id}/diff", response_model=ScriptDiffOut, summary="版本对比（M19）")
def diff_versions(
    script_id: int,
    db: DbSession,
    left: int = Query(..., ge=1, description="左侧版本号"),
    right: int = Query(..., ge=1, description="右侧版本号"),
    current_user: User = Depends(require_permission(Permission.脚本版本查看)),
) -> ScriptDiffOut:
    if not db.get(Script, script_id):
        raise not_found("脚本")

    def _get(version: int) -> ScriptVersion:
        row = db.scalar(
            select(ScriptVersion)
            .where(ScriptVersion.script_id == script_id, ScriptVersion.version == version)
            .order_by(ScriptVersion.id.desc())
        )
        if row is None:
            raise BizError(f"版本 v{version} 不存在")
        return row

    lv, rv = _get(left), _get(right)
    return ScriptDiffOut(
        left_version=lv.version,
        right_version=rv.version,
        left_content=lv.content_snapshot,
        right_content=rv.content_snapshot,
        diff=svc.make_diff(lv, rv),
    )


@router.post("/{script_id}/rollback", response_model=ScriptOut, summary="回退到历史版本（M19：保留回退记录）")
def rollback_script(
    script_id: int,
    payload: ScriptRollbackRequest,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.脚本版本回退)),
) -> ScriptOut:
    script = db.get(Script, script_id)
    if not script:
        raise not_found("脚本")
    target = db.scalar(
        select(ScriptVersion)
        .where(ScriptVersion.script_id == script_id, ScriptVersion.version == payload.version)
        .order_by(ScriptVersion.id.desc())
    )
    if target is None:
        raise BizError(f"版本 v{payload.version} 不存在")

    script.content = target.content_snapshot
    script.current_version += 1
    svc.add_version(
        db,
        script,
        target.content_snapshot,
        current_user.id,
        note=f"回退自 v{payload.version}",
    )
    script.modified_by = current_user.id
    script.modified_at = utcnow()
    db.commit()
    db.refresh(script)
    return svc.to_out(db, script)


@router.post("/{script_id}/submit", response_model=ScriptOut, summary="提交审核（草稿→待审核）")
def submit_script(script_id: int, _: CurrentUser, db: DbSession) -> ScriptOut:
    script = db.get(Script, script_id)
    if not script:
        raise not_found("脚本")
    if script.status != ScriptStatus.草稿:
        raise BizError(f"当前状态「{script.status.value}」不可提交审核")
    if not (script.content or "").strip():
        raise BizError("脚本正文不能为空")
    script.status = ScriptStatus.待审核
    db.commit()
    db.refresh(script)
    return svc.to_out(db, script)


@router.post("/{script_id}/review", response_model=ScriptOut, summary="脚本审核（4.8：一期仅管理员）")
def review_script(
    script_id: int, payload: ScriptReview, admin: AdminUser, db: DbSession
) -> ScriptOut:
    script = db.get(Script, script_id)
    if not script:
        raise not_found("脚本")
    if script.status != ScriptStatus.待审核:
        raise BizError(f"当前状态「{script.status.value}」不可审核")
    script.status = ScriptStatus.已通过 if payload.approved else ScriptStatus.已废弃
    script.reviewer_id = admin.id
    script.reviewed_at = utcnow()
    db.commit()
    db.refresh(script)
    return svc.to_out(db, script)


@router.post("/{script_id}/mark-used", response_model=ScriptOut, summary="标记已使用（R15/D4：仅已通过可标记）")
def mark_used(script_id: int, _: CurrentUser, db: DbSession) -> ScriptOut:
    script = db.get(Script, script_id)
    if not script:
        raise not_found("脚本")
    if script.status != ScriptStatus.已通过:
        raise BizError(f"仅「已通过」脚本可标记已使用，当前：{script.status.value}")
    script.status = ScriptStatus.已使用
    db.commit()

    # 选题派生状态：脚本被使用 → 选题「已使用」（context/04 §2）
    if script.topic_id:
        topic = db.get(Topic, script.topic_id)
        if topic and topic.status == TopicStatus.已生成脚本:
            topic.status = TopicStatus.已使用
            db.commit()
    db.refresh(script)
    return svc.to_out(db, script)


@router.post("/{script_id}/discard", response_model=ScriptOut, summary="废弃脚本")
def discard_script(script_id: int, _: CurrentUser, db: DbSession) -> ScriptOut:
    script = db.get(Script, script_id)
    if not script:
        raise not_found("脚本")
    if script.status in (ScriptStatus.已废弃, ScriptStatus.已使用):
        raise BizError(f"当前状态「{script.status.value}」不可废弃")
    script.status = ScriptStatus.已废弃
    db.commit()
    db.refresh(script)
    return svc.to_out(db, script)


@router.delete("/{script_id}", response_model=OkResult, summary="删除脚本（仅管理员）")
def delete_script(script_id: int, _: AdminUser, db: DbSession) -> OkResult:
    script = db.get(Script, script_id)
    if not script:
        raise not_found("脚本")
    db.delete(script)
    db.commit()
    return OkResult(message="脚本已删除")
