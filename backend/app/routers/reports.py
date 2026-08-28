"""数据报告 CRUD、生成/重试与飞书推送。路由 prefix 统一 /api。"""

import json
from datetime import datetime

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.exceptions import BizError, not_found
from app.models.base import utcnow
from app.models.report import (
    Report,
    ReportGenerationStatus,
    ReportPushRecord,
    ReportPushChannel,
    ReportPushStatus,
    ReportPushTask,
    ReportReviewStatus,
    ReportType,
)
from app.schemas.common import OkResult, PageResult
from app.schemas.report import (
    ReportCreate,
    ReportOut,
    ReportPushRecordOut,
    ReportPushTaskCreate,
    ReportPushTaskOut,
)
from app.services import feishu_push, report_executor

router = APIRouter(prefix="/api", tags=["数据报告"])

FEISHU_CONFIG_ERROR = (
    "未配置飞书推送，请联系管理员设置 "
    "FEISHU_APP_ID/FEISHU_APP_SECRET/FEISHU_PUSH_OPEN_IDS"
)


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


@router.get("/reports/push-config", summary="查询飞书推送配置状态")
def get_push_config(_: CurrentUser) -> dict[str, str | int | bool]:
    open_ids = [item.strip() for item in settings.feishu_push_open_ids.split(",") if item.strip()]
    return {
        "channel": "feishu",
        "receivers_count": len(open_ids),
        "configured": bool(settings.feishu_app_id and settings.feishu_app_secret and open_ids),
    }


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
    "/reports/push-tasks/{task_id}/cancel",
    response_model=ReportPushTaskOut,
    summary="取消推送任务",
)
def cancel_push_task(task_id: int, _: CurrentUser, db: DbSession) -> ReportPushTaskOut:
    task = db.scalar(
        select(ReportPushTask).options(selectinload(ReportPushTask.records)).where(ReportPushTask.id == task_id)
    )
    if not task:
        raise not_found("推送任务")
    if task.status not in {ReportPushStatus.待推送, ReportPushStatus.失败}:
        raise BizError("仅待推送或失败任务可取消")
    task.status = ReportPushStatus.已取消
    db.commit()
    return _push_out(task)


@router.delete(
    "/reports/push-tasks/{task_id}",
    response_model=OkResult,
    summary="删除推送任务",
)
def delete_push_task(task_id: int, _: CurrentUser, db: DbSession) -> OkResult:
    task = db.scalar(
        select(ReportPushTask).options(selectinload(ReportPushTask.records)).where(ReportPushTask.id == task_id)
    )
    if not task:
        raise not_found("推送任务")
    if task.status == ReportPushStatus.推送中:
        raise BizError("推送执行中，请稍后再试")
    if task.status == ReportPushStatus.已推送:
        raise BizError("已推送任务为发送凭证，不可删除")
    db.delete(task)
    db.commit()
    return OkResult(message="推送任务已删除")


@router.post(
    "/push-tasks/{task_id}/execute",
    response_model=ReportPushTaskOut,
    summary="执行飞书推送",
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
    if task.status == ReportPushStatus.已取消:
        raise BizError("已取消任务不可发送", code=409)

    if task.channel != ReportPushChannel.飞书:
        task.status = ReportPushStatus.待推送
        db.commit()
        raise BizError("当前仅支持飞书推送")

    open_ids = [item.strip() for item in settings.feishu_push_open_ids.split(",") if item.strip()]
    if not settings.feishu_app_id or not settings.feishu_app_secret or not open_ids:
        task.status = ReportPushStatus.待推送
        db.commit()
        raise BizError(FEISHU_CONFIG_ERROR)

    if task.status == ReportPushStatus.失败:
        task.retry_count = (task.retry_count or 0) + 1

    task.status = ReportPushStatus.推送中
    db.commit()

    report = db.get(Report, task.report_id)
    if report is None:
        task.status = ReportPushStatus.失败
        db.commit()
        raise not_found("报告")

    attempt_no = (task.retry_count or 0) + 1
    message_summary = _message_summary(task)
    config = task.message_config or {}
    title = str(config.get("title") or report.title)
    digest = str(config.get("summary") or report.summary or "")
    all_succeeded = True
    for open_id in open_ids:
        succeeded, response_summary = feishu_push.send_report_card(
            open_id,
            title,
            report.generated_at,
            digest,
            report.content,
            _report_overview(report),
        )
        response_data = _response_data(response_summary)
        provider_code = response_data.get("code")
        provider_message_id = response_data.get("message_id")
        db.add(
            ReportPushRecord(
                push_task_id=task.id,
                channel=task.channel,
                target_object=open_id,
                recipient_type=task.recipient_type,
                message_summary=message_summary,
                sent_at=utcnow() if succeeded else None,
                status=ReportPushStatus.已推送 if succeeded else ReportPushStatus.失败,
                provider_message_id=str(provider_message_id) if provider_message_id else None,
                error_code=None if succeeded else str(provider_code or "FEISHU_SEND_FAILED")[:64],
                error_message=None if succeeded else str(response_data.get("msg") or "飞书发送失败")[:2000],
                response_snapshot=response_data,
                attempt_no=attempt_no,
            )
        )
        all_succeeded = all_succeeded and succeeded

    task.status = ReportPushStatus.已推送 if all_succeeded else ReportPushStatus.失败
    db.commit()
    refreshed = db.scalar(
        select(ReportPushTask)
        .options(selectinload(ReportPushTask.records))
        .where(ReportPushTask.id == task.id)
        .execution_options(populate_existing=True)
    )
    return _push_out(refreshed or task)


def _report_overview(report: Report) -> str:
    parts = [
        f"报告类型：{report.report_type.value}",
        f"报告周期：{report.period_start.strftime('%Y-%m-%d')} 至 {report.period_end.strftime('%Y-%m-%d')}",
    ]
    snapshot = report.source_snapshot if isinstance(report.source_snapshot, dict) else {}
    sources = snapshot.get("sources")
    if isinstance(sources, list):
        parts.append(f"来源数量：{len(sources)}")
    return " ｜ ".join(parts)


def _message_summary(task: ReportPushTask) -> str:
    config = task.message_config or {}
    title = config.get("title") or ""
    summary = config.get("summary") or ""
    report_type = config.get("report_type") or ""
    parts = [str(item) for item in (title, report_type, summary) if item]
    text = " / ".join(parts) if parts else f"报告#{task.report_id} 推送摘要"
    return text[:2000]


def _response_data(summary: str) -> dict:
    try:
        data = json.loads(summary)
    except (TypeError, ValueError):
        return {"code": "FEISHU_INVALID_SUMMARY", "msg": "飞书响应摘要格式异常"}
    if isinstance(data, dict):
        return data
    return {"code": "FEISHU_INVALID_SUMMARY", "msg": "飞书响应摘要格式异常"}
