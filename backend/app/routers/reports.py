"""数据报告 CRUD、生成/重试与推送骨架。路由 prefix 统一 /api。"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.core.exceptions import BizError, not_found
from app.models.report import (
    Report,
    ReportGenerationStatus,
    ReportPushRecord,
    ReportPushStatus,
    ReportPushTask,
    ReportReviewStatus,
    ReportType,
)
from app.schemas.common import PageResult
from app.schemas.report import (
    ReportCreate,
    ReportOut,
    ReportPushRecordOut,
    ReportPushTaskCreate,
    ReportPushTaskOut,
)
from app.services import report_executor

router = APIRouter(prefix="/api", tags=["数据报告"])

# TODO(待实测): 飞书/微信渠道 API、授权方式、限流和消息格式均未确认，发送接口固定返回 501。
CHANNEL_NOT_IMPLEMENTED = "飞书/微信渠道 API 待实测，发送暂不可用"


def _no(prefix: str) -> str:
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def _default_title(report_type: ReportType, start: datetime, end: datetime) -> str:
    return f"{report_type.value}（{start.strftime('%Y-%m-%d')} 至 {end.strftime('%Y-%m-%d')}）"


def _push_out(task: ReportPushTask) -> ReportPushTaskOut:
    return ReportPushTaskOut(
        id=task.id,
        task_no=task.task_no,
        report_id=task.report_id,
        channel=task.channel,
        recipient_type=task.recipient_type,
        target_object=task.target_object,
        message_config=task.message_config,
        authorization_snapshot=task.authorization_snapshot,
        status=task.status,
        retry_count=task.retry_count,
        created_by=task.created_by,
        created_at=task.created_at,
        updated_at=task.updated_at,
        records=[ReportPushRecordOut.model_validate(row) for row in (task.records or [])],
    )


@router.get("/reports", response_model=PageResult[ReportOut], summary="报告列表")
def list_reports(
    _: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    report_type: ReportType | None = None,
    generation_status: ReportGenerationStatus | None = None,
) -> PageResult[ReportOut]:
    stmt = select(Report)
    if report_type is not None:
        stmt = stmt.where(Report.report_type == report_type)
    if generation_status is not None:
        stmt = stmt.where(Report.generation_status == generation_status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Report.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PageResult(
        total=total,
        page=page,
        page_size=page_size,
        items=[ReportOut.model_validate(row) for row in rows],
    )


@router.post("/reports", response_model=ReportOut, summary="创建报告（待生成，不执行）")
def create_report(payload: ReportCreate, current_user: CurrentUser, db: DbSession) -> ReportOut:
    report_no = _no("RP")
    title = (payload.title or "").strip() or _default_title(
        payload.report_type, payload.period_start, payload.period_end
    )
    row = Report(
        report_no=report_no,
        report_type=payload.report_type,
        title=title,
        period_start=payload.period_start,
        period_end=payload.period_end,
        template_id=payload.template_id,
        source_config=payload.source_config or {},
        summary="",
        content="",
        is_ai_product=True,
        generation_status=ReportGenerationStatus.待生成,
        review_status=ReportReviewStatus.默认通过,
        created_by=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ReportOut.model_validate(row)


@router.get("/reports/{report_id}", response_model=ReportOut, summary="报告详情")
def get_report(report_id: int, _: CurrentUser, db: DbSession) -> ReportOut:
    row = db.get(Report, report_id)
    if not row:
        raise not_found("报告")
    return ReportOut.model_validate(row)


@router.post("/reports/{report_id}/generate", response_model=ReportOut, summary="触发生成报告")
def generate_report(report_id: int, _: CurrentUser, db: DbSession) -> ReportOut:
    row = report_executor.generate_report(db, report_id)
    return ReportOut.model_validate(row)


@router.post("/reports/{report_id}/retry", response_model=ReportOut, summary="重试失败报告")
def retry_report(report_id: int, _: CurrentUser, db: DbSession) -> ReportOut:
    row = report_executor.retry_report(db, report_id)
    return ReportOut.model_validate(row)


@router.get(
    "/reports/{report_id}/push-tasks",
    response_model=PageResult[ReportPushTaskOut],
    summary="报告推送任务列表",
)
def list_report_push_tasks(
    report_id: int,
    _: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> PageResult[ReportPushTaskOut]:
    report = db.get(Report, report_id)
    if not report:
        raise not_found("报告")
    stmt = select(ReportPushTask).where(ReportPushTask.report_id == report_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.options(selectinload(ReportPushTask.records))
        .order_by(ReportPushTask.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PageResult(
        total=total,
        page=page,
        page_size=page_size,
        items=[_push_out(row) for row in rows],
    )


@router.post(
    "/reports/{report_id}/push-tasks",
    response_model=ReportPushTaskOut,
    summary="创建推送任务（不发送）",
)
def create_push_task(
    report_id: int,
    payload: ReportPushTaskCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ReportPushTaskOut:
    report = db.get(Report, report_id)
    if not report:
        raise not_found("报告")
    if report.generation_status != ReportGenerationStatus.已完成:
        raise BizError("只有已完成报告可创建推送任务")
    summary = (payload.message_config or {}).get("summary") or report.summary
    task = ReportPushTask(
        task_no=_no("PS"),
        report_id=report.id,
        channel=payload.channel,
        recipient_type=payload.recipient_type,
        target_object=payload.target_object,
        message_config=payload.message_config or {
            "title": report.title,
            "report_type": report.report_type.value,
            "summary": summary,
        },
        status=ReportPushStatus.待推送,
        created_by=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    task.records = []
    return _push_out(task)


@router.get("/push-tasks/{task_id}", response_model=ReportPushTaskOut, summary="推送任务详情")
def get_push_task(task_id: int, _: CurrentUser, db: DbSession) -> ReportPushTaskOut:
    task = db.scalar(
        select(ReportPushTask).options(selectinload(ReportPushTask.records)).where(ReportPushTask.id == task_id)
    )
    if not task:
        raise not_found("推送任务")
    return _push_out(task)


@router.post(
    "/push-tasks/{task_id}/execute",
    response_model=ReportPushTaskOut,
    summary="执行推送（渠道 API 待实测，返回 501）",
)
def execute_push_task(task_id: int, _: CurrentUser, db: DbSession) -> ReportPushTaskOut:
    task = db.scalar(
        select(ReportPushTask).options(selectinload(ReportPushTask.records)).where(ReportPushTask.id == task_id)
    )
    if not task:
        raise not_found("推送任务")
    if task.status == ReportPushStatus.已推送:
        raise BizError("已推送任务不可重复发送", code=409)
    if task.status == ReportPushStatus.推送中:
        raise BizError("推送任务执行中，禁止重复触发", code=409)

    if task.status == ReportPushStatus.失败:
        task.retry_count = (task.retry_count or 0) + 1

    task.status = ReportPushStatus.推送中
    db.commit()

    # TODO(待实测): 在此接入飞书/微信发送。不得把 token/key 写入记录或日志。
    attempt_no = (
        db.scalar(
            select(func.count()).select_from(ReportPushRecord).where(ReportPushRecord.push_task_id == task.id)
        )
        or 0
    ) + 1
    message_summary = _message_summary(task)
    record = ReportPushRecord(
        push_task_id=task.id,
        channel=task.channel,
        target_object=task.target_object,
        recipient_type=task.recipient_type,
        message_summary=message_summary,
        sent_at=None,
        status=ReportPushStatus.失败,
        error_code="CHANNEL_API_NOT_IMPLEMENTED",
        error_message=CHANNEL_NOT_IMPLEMENTED,
        response_snapshot={"implemented": False, "todo": "渠道 API 待实测"},
        attempt_no=attempt_no,
    )
    task.status = ReportPushStatus.失败
    db.add(record)
    db.commit()
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=CHANNEL_NOT_IMPLEMENTED)


def _message_summary(task: ReportPushTask) -> str:
    config = task.message_config or {}
    title = config.get("title") or ""
    summary = config.get("summary") or ""
    report_type = config.get("report_type") or ""
    parts = [str(item) for item in (title, report_type, summary) if item]
    text = " / ".join(parts) if parts else f"报告#{task.report_id} 推送摘要"
    return text[:2000]
