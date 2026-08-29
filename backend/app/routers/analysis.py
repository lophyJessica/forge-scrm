"""数据分析路由（模块 04）：数据源 / 原始数据 / 分析任务（同步执行）/ 结果审核 / 回写反哺。

红线：一期不实现自动采集逻辑与定时任务，data_source 仅保留结构（D5）。
D-T1：任务执行为同步，接口返回即出结果。
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy import func, select

from app.models.user import User
from app.core.deps import (
    AdminUser,
    CurrentUser,
    DbSession,
    allowed_data_source_ids,
    assert_data_source_visible,
    require_permission,
)
from app.core.enums import (
    AnalysisTaskStatus,
    BusinessObject,
    MaterialStatus,
    Permission,
    Specialty,
    TopicStatus,
    WritebackMaterialStatus,
    WritebackTopicStatus,
)
from app.core.exceptions import BizError, not_found
from app.core.logging import get_logger
from app.models.analysis import (
    AnalysisResult,
    AnalysisResultMaterial,
    AnalysisResultTopic,
    AnalysisTask,
    AnalysisTaskInput,
    DataSource,
    RawData,
)
from app.models.base import utcnow
from app.models.material import Material
from app.models.topic import Topic
from app.schemas.analysis import (
    AnalysisResultOut,
    AnalysisTaskCreate,
    AnalysisTaskOut,
    AnalysisTaskReview,
    DataSourceCreate,
    DataSourceOut,
    DataSourceUpdate,
    RawDataCreate,
    RawDataImportResult,
    RawDataOut,
    RawDataUpdate,
    WritebackMaterialRequest,
    WritebackTopicRequest,
)
from app.schemas.common import OkResult, PageResult
from app.services import analysis_service as svc
from app.services import deepseek_service as ds
from app.services import material_service as material_svc
from app.utils.csv_io import build_template, read_headers, sniff_rows, store_original

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["数据分析"])

RAW_DATA_CSV_HEADERS = ["数据源名称", "原始内容", "采集时间", "时间窗开始", "时间窗结束", "结构化字段JSON"]
RAW_DATA_CSV_REQUIRED = ["数据源名称", "原始内容", "时间窗开始", "时间窗结束"]


# ==================== 数据源（不实现采集逻辑，D5）====================

@router.get("/data-sources", response_model=PageResult[DataSourceOut], summary="数据源列表")
def list_data_sources(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    business_object: BusinessObject | None = None,
    keyword: str | None = None,
) -> PageResult[DataSourceOut]:
    stmt = select(DataSource)
    scope = allowed_data_source_ids(current_user)
    if scope is not None:
        stmt = stmt.where(DataSource.id.in_(scope or [0]))
    if business_object is not None:
        stmt = stmt.where(DataSource.business_object == business_object)
    if keyword:
        stmt = stmt.where(DataSource.name.like(f"%{keyword}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(DataSource.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PageResult[DataSourceOut](
        total=total, page=page, page_size=page_size,
        items=[DataSourceOut.model_validate(r) for r in rows],
    )


@router.post("/data-sources", response_model=DataSourceOut, summary="新增数据源（仅管理员）")
def create_data_source(payload: DataSourceCreate, _: AdminUser, db: DbSession) -> DataSourceOut:
    if payload.business_object in (BusinessObject.自己账号, BusinessObject.对标账号) and not payload.account_identifier:
        raise BizError("账号类数据源必须填写账号标识")
    source = DataSource(**payload.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return DataSourceOut.model_validate(source)


@router.get("/data-sources/{source_id}", response_model=DataSourceOut, summary="数据源详情")
def get_data_source(source_id: int, current_user: CurrentUser, db: DbSession) -> DataSourceOut:
    source = db.get(DataSource, source_id)
    if not source:
        raise not_found("数据源")
    assert_data_source_visible(current_user, source_id)
    return DataSourceOut.model_validate(source)


@router.put("/data-sources/{source_id}", response_model=DataSourceOut, summary="修改数据源（仅管理员）")
def update_data_source(
    source_id: int, payload: DataSourceUpdate, _: AdminUser, db: DbSession
) -> DataSourceOut:
    source = db.get(DataSource, source_id)
    if not source:
        raise not_found("数据源")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(source, k, v)
    db.commit()
    db.refresh(source)
    return DataSourceOut.model_validate(source)


@router.delete("/data-sources/{source_id}", response_model=OkResult, summary="删除数据源（仅管理员）")
def delete_data_source(source_id: int, _: AdminUser, db: DbSession) -> OkResult:
    source = db.get(DataSource, source_id)
    if not source:
        raise not_found("数据源")
    if db.scalar(select(func.count()).select_from(RawData).where(RawData.source_id == source_id)):
        raise BizError("该数据源下已有原始数据，不能删除；可改为「停用」")
    db.delete(source)
    db.commit()
    return OkResult(message="数据源已删除")


# ==================== 原始数据（手动录入 + CSV 导入）====================

@router.get("/raw-data/csv-template", summary="下载原始数据导入模板（D-T2）")
def raw_data_csv_template(_: CurrentUser) -> Response:
    sample = [
        [
            "自己账号-视频号",
            "视频标题/文案/评论等原始文本",
            "2026-08-20 10:00:00",
            "2026-08-01",
            "2026-08-20",
            '{"播放量":12000,"点赞":320}',
        ]
    ]
    return Response(
        content=build_template(RAW_DATA_CSV_HEADERS, sample),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="raw_data_import_template.csv"'},
    )


@router.post("/raw-data/import", response_model=RawDataImportResult, summary="CSV 导入原始数据")
def import_raw_data(
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.数据录入导入)),
    file: UploadFile = File(..., description="按模板导出的 CSV/TXT"),
) -> RawDataImportResult:
    raw = file.file.read()
    if not raw:
        raise BizError("文件为空")
    try:
        headers = read_headers(raw)
        rows = sniff_rows(raw)
    except ValueError as exc:
        raise BizError(str(exc))

    missing = [c for c in RAW_DATA_CSV_REQUIRED if c not in headers]
    if missing:
        raise BizError(f"模板列名不匹配，缺少必需列：{', '.join(missing)}")

    stored = store_original(raw, file.filename or "raw_data.csv", "rawdata")
    source_map = {s.name: s for s in db.scalars(select(DataSource)).all()}
    errors: list[dict] = []
    success = 0

    for idx, row in enumerate(rows, start=2):
        try:
            source = source_map.get(row.get("数据源名称", "").strip())
            if source is None:
                raise ValueError(f"数据源「{row.get('数据源名称', '')}」不存在")
            assert_data_source_visible(current_user, source.id)
            content = row.get("原始内容", "").strip()
            if not content:
                raise ValueError("原始内容为空")
            window_start = _parse_dt(row.get("时间窗开始", ""), "时间窗开始")
            window_end = _parse_dt(row.get("时间窗结束", ""), "时间窗结束")
            if window_end < window_start:
                raise ValueError("时间窗结束早于开始")
            collected_raw = (row.get("采集时间") or "").strip()
            collected_at = _parse_dt(collected_raw, "采集时间") if collected_raw else utcnow()

            structured = None
            structured_raw = (row.get("结构化字段JSON") or "").strip()
            if structured_raw:
                import json

                try:
                    structured = json.loads(structured_raw)
                except json.JSONDecodeError:
                    raise ValueError("结构化字段JSON 不是合法 JSON")

            db.add(
                RawData(
                    source_id=source.id,
                    collected_at=collected_at,
                    raw_content=content,
                    structured=structured,
                    window_start=window_start,
                    window_end=window_end,
                    clean_dedup_record={"import_file": stored, "row": idx},
                )
            )
            db.flush()
            success += 1
        except Exception as exc:  # 单行失败不影响其他行
            db.rollback()
            errors.append({"row": idx, "message": str(exc)})

    db.commit()
    logger.info("原始数据导入：成功 %s 行，失败 %s 行，原文件 %s", success, len(errors), stored)
    return RawDataImportResult(
        total=len(rows), success=success, failed=len(errors), errors=errors, stored_file=stored
    )


def _parse_dt(value: str, field: str) -> datetime:
    text = (value or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"{field} 格式错误，应为 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS")


@router.get("/raw-data", response_model=PageResult[RawDataOut], summary="原始数据列表")
def list_raw_data(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    source_id: int | None = None,
    keyword: str | None = None,
) -> PageResult[RawDataOut]:
    stmt = select(RawData)
    scope = allowed_data_source_ids(current_user)
    if scope is not None:
        stmt = stmt.where(RawData.source_id.in_(scope or [0]))
    if source_id is not None:
        assert_data_source_visible(current_user, source_id)
        stmt = stmt.where(RawData.source_id == source_id)
    if keyword:
        stmt = stmt.where(RawData.raw_content.like(f"%{keyword}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(RawData.collected_at.desc(), RawData.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PageResult[RawDataOut](
        total=total, page=page, page_size=page_size, items=[svc.raw_to_out(r) for r in rows]
    )


@router.post("/raw-data", response_model=RawDataOut, summary="手动录入原始数据")
def create_raw_data(
    payload: RawDataCreate,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.数据录入导入)),
) -> RawDataOut:
    source = db.get(DataSource, payload.source_id)
    if not source:
        raise not_found("数据源")
    assert_data_source_visible(current_user, source.id)
    if payload.window_end < payload.window_start:
        raise BizError("时间窗结束早于开始")

    row = RawData(
        source_id=payload.source_id,
        collected_at=payload.collected_at or utcnow(),
        raw_content=payload.raw_content,
        structured=payload.structured,
        window_start=payload.window_start,
        window_end=payload.window_end,
        clean_dedup_record=payload.clean_dedup_record or {"method": "手动录入"},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return svc.raw_to_out(row)


@router.get("/raw-data/{raw_id}", response_model=RawDataOut, summary="原始数据详情")
def get_raw_data(raw_id: int, current_user: CurrentUser, db: DbSession) -> RawDataOut:
    row = db.get(RawData, raw_id)
    if not row:
        raise not_found("原始数据")
    assert_data_source_visible(current_user, row.source_id)
    return svc.raw_to_out(row)


@router.put("/raw-data/{raw_id}", response_model=RawDataOut, summary="修改原始数据")
def update_raw_data(
    raw_id: int,
    payload: RawDataUpdate,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.数据录入导入)),
) -> RawDataOut:
    row = db.get(RawData, raw_id)
    if not row:
        raise not_found("原始数据")
    assert_data_source_visible(current_user, row.source_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    if row.window_end < row.window_start:
        raise BizError("时间窗结束早于开始")
    db.commit()
    db.refresh(row)
    return svc.raw_to_out(row)


@router.delete("/raw-data/{raw_id}", response_model=OkResult, summary="删除原始数据（仅管理员）")
def delete_raw_data(raw_id: int, _: AdminUser, db: DbSession) -> OkResult:
    row = db.get(RawData, raw_id)
    if not row:
        raise not_found("原始数据")
    db.delete(row)
    db.commit()
    return OkResult(message="原始数据已删除")


# ==================== 分析任务（同步执行，D-T1）====================

@router.get("/analysis-tasks", response_model=PageResult[AnalysisTaskOut], summary="分析任务列表")
def list_tasks(
    _: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: AnalysisTaskStatus | None = None,
) -> PageResult[AnalysisTaskOut]:
    stmt = select(AnalysisTask)
    if status is not None:
        stmt = stmt.where(AnalysisTask.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(AnalysisTask.created_at.desc(), AnalysisTask.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PageResult[AnalysisTaskOut](
        total=total, page=page, page_size=page_size, items=[svc.task_to_out(db, r) for r in rows]
    )


@router.post("/analysis-tasks", response_model=AnalysisTaskOut, summary="创建分析任务（待执行）")
def create_task(
    payload: AnalysisTaskCreate,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.分析任务执行)),
) -> AnalysisTaskOut:
    rows = list(db.scalars(select(RawData).where(RawData.id.in_(payload.raw_data_ids))).all())
    missing = set(payload.raw_data_ids) - {r.id for r in rows}
    if missing:
        raise BizError(f"原始数据不存在：{sorted(missing)}")
    for r in rows:
        assert_data_source_visible(current_user, r.source_id)

    _, _, prompt_snapshot, material_snapshot, output_schema = svc.build_prompt(
        db, payload.type.value, rows, payload.material_ids, payload.prompt_template_id
    )

    task = AnalysisTask(
        name=payload.name,
        type=payload.type,
        prompt_version_snapshot=prompt_snapshot,
        material_context_snapshot=material_snapshot,
        output_schema=payload.output_schema or output_schema,
        status=AnalysisTaskStatus.待执行,
        created_by=current_user.id,
        retry_count=0,
    )
    db.add(task)
    db.flush()
    for rid in dict.fromkeys(payload.raw_data_ids):
        db.add(AnalysisTaskInput(task_id=task.id, raw_data_id=rid))
    db.commit()
    db.refresh(task)
    return svc.task_to_out(db, task)


@router.post("/analysis-tasks/{task_id}/execute", response_model=AnalysisTaskOut, summary="执行分析任务（同步，D-T1）")
def execute_task(
    task_id: int,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.分析任务执行)),
    prompt_template_id: int | None = Query(None, description="覆盖任务创建时的提示词模板"),
) -> AnalysisTaskOut:
    task = db.get(AnalysisTask, task_id)
    if not task:
        raise not_found("分析任务")
    if task.status not in (AnalysisTaskStatus.待执行, AnalysisTaskStatus.失败):
        raise BizError(f"当前状态「{task.status.value}」不可执行（仅待执行/失败可执行或重试）")

    raw_ids = [
        i.raw_data_id
        for i in db.scalars(select(AnalysisTaskInput).where(AnalysisTaskInput.task_id == task.id)).all()
    ]
    rows = list(db.scalars(select(RawData).where(RawData.id.in_(raw_ids))).all())
    if not rows:
        raise BizError("任务没有可分析的原始数据")

    material_ids = (task.material_context_snapshot or {}).get("material_ids", [])
    template_id = prompt_template_id
    if template_id is None and task.prompt_version_snapshot:
        template_id = task.prompt_version_snapshot.get("template_id")

    system_prompt, user_prompt, prompt_snapshot, material_snapshot, output_schema = svc.build_prompt(
        db, task.type.value, rows, material_ids, template_id
    )
    task.status = AnalysisTaskStatus.执行中
    task.error_message = None
    db.commit()

    try:
        results, raw = ds.chat_json(system_prompt, user_prompt, validator=svc.validate_analysis_payload)
    except ds.DeepSeekError as exc:
        archive = ds.archive_raw(exc.raw, "analysis_failed")
        task.status = AnalysisTaskStatus.失败
        task.ai_raw_response = exc.raw
        task.error_message = f"{exc.message}；原始响应留档：{archive}"
        task.retry_count = (task.retry_count or 0) + 1
        db.commit()
        db.refresh(task)
        logger.error("分析任务 %s 执行失败：%s", task.id, exc.message)
        raise BizError(f"分析任务执行失败，可重试。原因：{exc.message}；原始响应留档：{archive}")

    ds.archive_raw(raw, "analysis")
    # 重跑：清掉旧结果，避免重复
    db.query(AnalysisResult).filter(AnalysisResult.task_id == task.id).delete()
    db.flush()
    for item in results:
        db.add(
            AnalysisResult(
                task_id=task.id,
                result_content=item,
                writeback_material_status=WritebackMaterialStatus.未回写,
                writeback_topic_status=WritebackTopicStatus.未反哺,
            )
        )
    task.ai_raw_response = raw
    task.prompt_version_snapshot = prompt_snapshot or task.prompt_version_snapshot
    task.material_context_snapshot = material_snapshot or task.material_context_snapshot
    task.output_schema = task.output_schema or output_schema
    task.status = AnalysisTaskStatus.待审核  # 结果必须人工审核（R6）
    task.error_message = None
    db.commit()
    db.refresh(task)
    logger.info("分析任务 %s 执行成功，产出 %s 条结果", task.id, len(results))
    return svc.task_to_out(db, task)


@router.get("/analysis-tasks/{task_id}", response_model=AnalysisTaskOut, summary="分析任务详情")
def get_task(task_id: int, _: CurrentUser, db: DbSession) -> AnalysisTaskOut:
    task = db.get(AnalysisTask, task_id)
    if not task:
        raise not_found("分析任务")
    return svc.task_to_out(db, task)


@router.get("/analysis-tasks/{task_id}/ai-raw", summary="查看任务 AI 原始响应留档（S04）")
def get_task_ai_raw(task_id: int, _: CurrentUser, db: DbSession) -> dict:
    task = db.get(AnalysisTask, task_id)
    if not task:
        raise not_found("分析任务")
    return {
        "task_id": task.id,
        "status": task.status,
        "ai_raw_response": task.ai_raw_response,
        "error_message": task.error_message,
        "prompt_version_snapshot": task.prompt_version_snapshot,
    }


@router.post("/analysis-tasks/{task_id}/review", response_model=AnalysisTaskOut, summary="分析结果人工审核（R6）")
def review_task(
    task_id: int,
    payload: AnalysisTaskReview,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.分析结果审核)),
) -> AnalysisTaskOut:
    task = db.get(AnalysisTask, task_id)
    if not task:
        raise not_found("分析任务")
    if task.status != AnalysisTaskStatus.待审核:
        raise BizError(f"当前状态「{task.status.value}」不可审核")
    task.status = AnalysisTaskStatus.已确认 if payload.approved else AnalysisTaskStatus.已废弃
    task.reviewer_id = current_user.id
    task.reviewed_at = utcnow()
    db.commit()
    db.refresh(task)
    return svc.task_to_out(db, task)


@router.delete("/analysis-tasks/{task_id}", response_model=OkResult, summary="删除分析任务（仅管理员）")
def delete_task(task_id: int, _: AdminUser, db: DbSession) -> OkResult:
    task = db.get(AnalysisTask, task_id)
    if not task:
        raise not_found("分析任务")
    db.delete(task)
    db.commit()
    return OkResult(message="分析任务已删除")


# ==================== 分析结果 / 回写 / 反哺（两个独立动作）====================

@router.get("/analysis-results", response_model=PageResult[AnalysisResultOut], summary="分析结果列表")
def list_results(
    _: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    task_id: int | None = None,
) -> PageResult[AnalysisResultOut]:
    stmt = select(AnalysisResult)
    if task_id is not None:
        stmt = stmt.where(AnalysisResult.task_id == task_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(AnalysisResult.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PageResult[AnalysisResultOut](
        total=total, page=page, page_size=page_size, items=[svc.result_to_out(db, r) for r in rows]
    )


@router.get("/analysis-results/{result_id}", response_model=AnalysisResultOut, summary="分析结果详情")
def get_result(result_id: int, _: CurrentUser, db: DbSession) -> AnalysisResultOut:
    result = db.get(AnalysisResult, result_id)
    if not result:
        raise not_found("分析结果")
    return svc.result_to_out(db, result)


def _assert_confirmed(db, result: AnalysisResult) -> AnalysisTask:
    task = db.get(AnalysisTask, result.task_id)
    if task is None:
        raise not_found("分析任务")
    if task.status != AnalysisTaskStatus.已确认:
        raise BizError("分析结果必须先人工审核确认，才能回写/反哺（R6）")
    return task


@router.post(
    "/analysis-results/{result_id}/writeback-material",
    response_model=AnalysisResultOut,
    summary="回写资料库（独立动作；产物为草稿，需按 R1 审核）",
)
def writeback_material(
    result_id: int,
    payload: WritebackMaterialRequest,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.回写反哺)),
) -> AnalysisResultOut:
    result = db.get(AnalysisResult, result_id)
    if not result:
        raise not_found("分析结果")
    task = _assert_confirmed(db, result)

    for item in payload.materials:
        if item.valid_until < item.valid_from:
            raise BizError("有效期止早于有效期起")
        material = Material(
            title=item.title,
            content=item.content,
            class_id=item.class_id,
            source_type=item.source_type,
            trust_level=item.trust_level,
            valid_from=item.valid_from,
            valid_until=item.valid_until,
            status=MaterialStatus.待审核,  # AI 产物必须走审核（R1/R7）
            is_ai_product=True,
            source_analysis_task_id=task.id,
            created_by=current_user.id,
        )
        db.add(material)
        db.flush()
        if item.tags:
            tags = material_svc.resolve_tags(db, item.tags, current_user.id)
            material_svc.set_material_tags(db, material, tags)
        db.add(AnalysisResultMaterial(result_id=result.id, material_id=material.id))

    result.writeback_material_status = WritebackMaterialStatus.已回写
    db.commit()
    db.refresh(result)
    return svc.result_to_out(db, result)


@router.post(
    "/analysis-results/{result_id}/writeback-topic",
    response_model=AnalysisResultOut,
    summary="反哺选题库（独立动作；产物为待筛选，需按 R3 人工筛选）",
)
def writeback_topic(
    result_id: int,
    payload: WritebackTopicRequest,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.回写反哺)),
) -> AnalysisResultOut:
    result = db.get(AnalysisResult, result_id)
    if not result:
        raise not_found("分析结果")
    _assert_confirmed(db, result)

    valid_specialties = {e.value for e in Specialty}
    for item in payload.topics:
        if item.specialty not in valid_specialties:
            raise BizError(f"专业方向「{item.specialty}」不在枚举内")
        topic = Topic(
            title=item.title,
            direction=item.direction,
            specialty=Specialty(item.specialty),
            customer_scenario=item.customer_scenario,
            user_perspective=item.user_perspective,
            business_direction=item.business_direction,
            core_angle=item.core_angle,
            topic_principle=item.topic_principle,
            topic_angle=item.topic_angle,
            status=TopicStatus.待筛选,
            batch_no=None,
            ai_raw_response=None,
            created_by=current_user.id,
        )
        db.add(topic)
        db.flush()
        db.add(AnalysisResultTopic(result_id=result.id, topic_id=topic.id))

    result.writeback_topic_status = WritebackTopicStatus.已反哺
    db.commit()
    db.refresh(result)
    return svc.result_to_out(db, result)
