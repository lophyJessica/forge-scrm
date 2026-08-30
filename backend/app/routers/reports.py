"""数据报告 CRUD、生成/重试与飞书推送。路由 prefix 统一 /api。"""

import json
import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, delete, func, select, update
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession, require_permission
from app.core.enums import Permission
from app.core.exceptions import BizError, not_found
from app.models.base import utcnow
from app.models.report import (
    Report,
    ReportGenerationStatus,
    ReportPushRecord,
    ReportPushRecordStatus,
    ReportPushChannel,
    ReportPushStatus,
    ReportPushTask,
    ReportReviewStatus,
    ReportType,
    ReportTemplate,
)
from app.core.enums import PromptStatus
from app.models.user import User
from app.schemas.common import OkResult, PageResult
from app.schemas.report import (
    ReportCreate,
    ReportOut,
    ReportTemplateCreate,
    ReportTemplateOut,
    ReportTemplateUpdate,
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
PUSH_STALE_AFTER = timedelta(minutes=10)


def _no(prefix: str) -> str:
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def _default_title(report_type: ReportType, start: datetime, end: datetime) -> str:
    return f"{report_type.value}（{start.strftime('%Y-%m-%d')} 至 {end.strftime('%Y-%m-%d')}）"


def _set_default_template(db, template: ReportTemplate) -> None:
    db.query(ReportTemplate).filter(
        ReportTemplate.report_type == template.report_type,
        ReportTemplate.id != template.id,
    ).update({ReportTemplate.is_default: False}, synchronize_session=False)
    template.is_default = True


@router.get("/report-templates", response_model=PageResult[ReportTemplateOut], summary="报告模板列表")
def list_report_templates(
    _: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    report_type: ReportType | None = None,
    status: PromptStatus | None = None,
    keyword: str | None = None,
) -> PageResult[ReportTemplateOut]:
    stmt = select(ReportTemplate)
    if report_type is not None:
        stmt = stmt.where(ReportTemplate.report_type == report_type)
    if status is not None:
        stmt = stmt.where(ReportTemplate.status == status)
    if keyword:
        stmt = stmt.where(ReportTemplate.name.like(f"%{keyword}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(ReportTemplate.is_default.desc(), ReportTemplate.created_at.desc(), ReportTemplate.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PageResult(total=total, page=page, page_size=page_size, items=[ReportTemplateOut.model_validate(row) for row in rows])


@router.post("/report-templates", response_model=ReportTemplateOut, summary="新建报告模板")
def create_report_template(payload: ReportTemplateCreate, db: DbSession, admin: User = Depends(require_permission(Permission.提示词配置))) -> ReportTemplateOut:
    template = ReportTemplate(
        report_type=payload.report_type,
        name=payload.name.strip(),
        content_schema=payload.content_schema,
        is_default=False,
        status=payload.status,
        created_by=admin.id,
    )
    db.add(template)
    db.flush()
    if payload.is_default:
        _set_default_template(db, template)
    db.commit()
    db.refresh(template)
    return ReportTemplateOut.model_validate(template)


@router.get("/report-templates/{template_id}", response_model=ReportTemplateOut, summary="报告模板详情")
def get_report_template(template_id: int, _: CurrentUser, db: DbSession) -> ReportTemplateOut:
    template = db.get(ReportTemplate, template_id)
    if not template:
        raise not_found("报告模板")
    return ReportTemplateOut.model_validate(template)


@router.put("/report-templates/{template_id}", response_model=ReportTemplateOut, summary="修改报告模板")
def update_report_template(
    template_id: int,
    payload: ReportTemplateUpdate,
    db: DbSession,
    admin: User = Depends(require_permission(Permission.提示词配置)),
) -> ReportTemplateOut:
    template = db.get(ReportTemplate, template_id)
    if not template:
        raise not_found("报告模板")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        data["name"] = data["name"].strip()
    previous_type = template.report_type
    wants_default = data.pop("is_default", None)
    for key, value in data.items():
        setattr(template, key, value)
    if template.status != PromptStatus.启用:
        template.is_default = False
    if wants_default:
        if template.status != PromptStatus.启用:
            raise BizError("停用模板不能设为默认")
        _set_default_template(db, template)
    elif wants_default is False and template.is_default:
        template.is_default = False
    if previous_type != template.report_type and template.is_default:
        _set_default_template(db, template)
    db.commit()
    db.refresh(template)
    return ReportTemplateOut.model_validate(template)


@router.post("/report-templates/{template_id}/set-default", response_model=ReportTemplateOut, summary="设为默认报告模板")
def set_default_report_template(template_id: int, db: DbSession, admin: User = Depends(require_permission(Permission.提示词配置))) -> ReportTemplateOut:
    template = db.get(ReportTemplate, template_id)
    if not template:
        raise not_found("报告模板")
    if template.status != PromptStatus.启用:
        raise BizError("停用模板不能设为默认")
    _set_default_template(db, template)
    db.commit()
    db.refresh(template)
    return ReportTemplateOut.model_validate(template)


@router.delete("/report-templates/{template_id}", response_model=OkResult, summary="删除报告模板")
def delete_report_template(template_id: int, db: DbSession, admin: User = Depends(require_permission(Permission.提示词配置))) -> OkResult:
    template = db.get(ReportTemplate, template_id)
    if not template:
        raise not_found("报告模板")
    if db.scalar(select(func.count()).select_from(Report).where(Report.template_id == template_id)):
        raise BizError("已有报告使用该模板，不能删除；可停用模板")
    db.delete(template)
    db.commit()
    return OkResult(message="报告模板已删除")


def _push_out(task: ReportPushTask) -> ReportPushTaskOut:
    return ReportPushTaskOut(
        id=task.id,
        task_no=task.task_no,
        report_id=task.report_id,
        channel=task.channel,
        recipient_type=task.recipient_type,
        target_object=_mask_open_id(task.target_object),
        message_config=task.message_config,
        authorization_snapshot=task.authorization_snapshot,
        status=task.status,
        retry_count=task.retry_count,
        created_by=task.created_by,
        created_at=task.created_at,
        updated_at=task.updated_at,
        records=[_push_record_out(row) for row in (task.records or [])],
    )


def _push_record_out(record: ReportPushRecord) -> ReportPushRecordOut:
    out = ReportPushRecordOut.model_validate(record)
    return out.model_copy(update={"target_object": _mask_open_id(out.target_object)})


def _mask_open_id(value: str) -> str:
    if value.startswith("ou_") and len(value) > 10:
        return f"{value[:6]}****{value[-4:]}"
    return value


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
        stmt.order_by(Report.generated_at.desc(), Report.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PageResult(
        total=total,
        page=page,
        page_size=page_size,
        items=[ReportOut.model_validate(row) for row in rows],
    )


@router.post("/reports", response_model=ReportOut, summary="创建报告（待生成，不执行）")
def create_report(payload: ReportCreate, current_user: CurrentUser, db: DbSession) -> ReportOut:
    if payload.template_id is not None:
        template = db.get(ReportTemplate, payload.template_id)
        if template is None:
            raise not_found("报告模板")
        if template.report_type != payload.report_type:
            raise BizError("报告模板类型与报告类型不匹配")
        if template.status != PromptStatus.启用:
            raise BizError("停用模板不能用于新报告")
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


@router.delete("/reports/{report_id}", response_model=OkResult, summary="删除报告")
def delete_report(
    report_id: int,
    db: DbSession,
    _: User = Depends(require_permission(Permission.报告推送)),
) -> OkResult:
    report = db.get(Report, report_id)
    if not report:
        raise not_found("报告")
    if report.generation_status == ReportGenerationStatus.生成中:
        raise BizError("报告生成中，不可删除")
    push_task_id = db.scalar(
        select(ReportPushTask.id).where(ReportPushTask.report_id == report_id).limit(1)
    )
    if push_task_id is not None:
        raise BizError("该报告已有推送记录，为保持对账完整不可删除")
    db.delete(report)
    db.commit()
    return OkResult(message="报告已删除")


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
        .order_by(ReportPushTask.created_at.desc(), ReportPushTask.id.desc())
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
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.报告推送)),
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
        target_object=_mask_open_id(payload.target_object),
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
def cancel_push_task(
    task_id: int,
    db: DbSession,
    _: User = Depends(require_permission(Permission.报告推送)),
) -> ReportPushTaskOut:
    task = _get_push_task(db, task_id)
    if not task:
        raise not_found("推送任务")
    task = _reset_stale_push(db, task)
    if task is None:
        raise BizError("任务状态已变更，请刷新后操作", code=409)
    result = db.execute(
        update(ReportPushTask)
        .where(
            ReportPushTask.id == task_id,
            ReportPushTask.status.in_([ReportPushStatus.待推送, ReportPushStatus.失败]),
        )
        .values(status=ReportPushStatus.已取消, updated_at=utcnow())
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        raise BizError("任务状态已变更，请刷新后操作", code=409)
    db.commit()
    return _push_out(_get_push_task(db, task_id))


@router.delete(
    "/reports/push-tasks/{task_id}",
    response_model=OkResult,
    summary="删除推送任务",
)
def delete_push_task(
    task_id: int,
    db: DbSession,
    _: User = Depends(require_permission(Permission.报告推送)),
) -> OkResult:
    task = db.get(ReportPushTask, task_id)
    if not task:
        raise not_found("推送任务")
    result = db.execute(
        delete(ReportPushTask)
        .where(
            ReportPushTask.id == task_id,
            ReportPushTask.status.notin_([ReportPushStatus.推送中, ReportPushStatus.已推送]),
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        current = db.get(ReportPushTask, task_id)
        if current and current.status == ReportPushStatus.推送中:
            raise BizError("推送执行中，请稍后再试")
        if current and current.status == ReportPushStatus.已推送:
            raise BizError("已推送任务为发送凭证，不可删除")
        raise BizError("任务状态已变更，请刷新后操作", code=409)
    db.commit()
    return OkResult(message="推送任务已删除")


@router.post(
    "/push-tasks/{task_id}/execute",
    response_model=ReportPushTaskOut,
    summary="执行飞书推送",
)
def execute_push_task(
    task_id: int,
    db: DbSession,
    _: User = Depends(require_permission(Permission.报告推送)),
) -> ReportPushTaskOut:
    task = _get_push_task(db, task_id)
    if not task:
        raise not_found("推送任务")
    task = _reset_stale_push(db, task)
    if task is None:
        raise BizError("任务状态已变更，请刷新后操作", code=409)

    if task.channel != ReportPushChannel.飞书:
        raise BizError("当前仅支持飞书推送")

    open_ids = [item.strip() for item in settings.feishu_push_open_ids.split(",") if item.strip()]
    if not settings.feishu_app_id or not settings.feishu_app_secret or not open_ids:
        raise BizError(FEISHU_CONFIG_ERROR)

    sent_targets = {
        _mask_open_id(record.target_object)
        for record in task.records
        if record.status == ReportPushRecordStatus.已推送
    }
    pending_open_ids = [
        open_id for open_id in open_ids if _mask_open_id(open_id) not in sent_targets
    ]
    if not pending_open_ids:
        raise BizError("所有接收人已推送成功")

    result = db.execute(
        update(ReportPushTask)
        .where(
            ReportPushTask.id == task_id,
            ReportPushTask.status.in_([ReportPushStatus.待推送, ReportPushStatus.失败]),
        )
        .values(
            status=ReportPushStatus.推送中,
            retry_count=case(
                (
                    ReportPushTask.status == ReportPushStatus.失败,
                    ReportPushTask.retry_count + 1,
                ),
                else_=ReportPushTask.retry_count,
            ),
            updated_at=utcnow(),
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        raise BizError("任务状态已变更，请刷新后操作", code=409)
    db.commit()
    task = _get_push_task(db, task_id)
    if task is None:
        raise BizError("任务状态已变更，请刷新后操作", code=409)

    attempt_no = (task.retry_count or 0) + 1
    message_summary = "报告推送"
    current_target = task.target_object
    try:
        report = db.get(Report, task.report_id)
        if report is None:
            raise RuntimeError("关联报告不存在")
        message_summary = _message_summary(task)
        config = task.message_config or {}
        title = str(config.get("title") or report.title)
        digest = str(config.get("summary") or report.summary or "")
        all_succeeded = True
        for open_id in pending_open_ids:
            current_target = _mask_open_id(open_id)
            push_result = feishu_push.send_report_card(
                open_id,
                title,
                report.generated_at,
                digest,
                report.content,
                _report_overview(report),
            )
            succeeded = push_result.ok
            response_summary = push_result.summary
            record_message_summary = (
                f"{message_summary} / 卡片2.0降级"
                if push_result.downgraded
                else message_summary
            )
            response_data = _safe_response_data(
                _response_data(response_summary), open_ids
            )
            provider_code = response_data.get("code")
            provider_message_id = response_data.get("message_id")
            db.add(
                ReportPushRecord(
                    push_task_id=task.id,
                    channel=task.channel,
                    target_object=_mask_open_id(open_id),
                    recipient_type=task.recipient_type,
                    message_summary=record_message_summary,
                    sent_at=utcnow() if succeeded else None,
                    status=(
                        ReportPushRecordStatus.已推送
                        if succeeded
                        else ReportPushRecordStatus.失败
                    ),
                    provider_message_id=str(provider_message_id) if provider_message_id else None,
                    error_code=None if succeeded else str(provider_code or "FEISHU_SEND_FAILED")[:64],
                    error_message=None if succeeded else str(response_data.get("msg") or "飞书发送失败")[:2000],
                    response_snapshot=response_data,
                    attempt_no=attempt_no,
                )
            )
            db.commit()
            all_succeeded = all_succeeded and succeeded
    except Exception as exc:
        db.rollback()
        task = db.get(ReportPushTask, task_id)
        if task is None:
            raise not_found("推送任务")
        task.status = ReportPushStatus.失败
        error_message = _safe_exception_summary(exc, open_ids)
        db.add(
            ReportPushRecord(
                push_task_id=task.id,
                channel=task.channel,
                target_object=current_target,
                recipient_type=task.recipient_type,
                message_summary=message_summary,
                status=ReportPushRecordStatus.失败,
                error_code="UNEXPECTED_PUSH_ERROR",
                error_message=error_message,
                response_snapshot={"code": "UNEXPECTED_PUSH_ERROR", "msg": error_message},
                attempt_no=attempt_no,
            )
        )
        db.commit()
        refreshed = _get_push_task(db, task_id)
        return _push_out(refreshed or task)

    task.status = ReportPushStatus.已推送 if all_succeeded else ReportPushStatus.失败
    db.commit()
    refreshed = db.scalar(
        select(ReportPushTask)
        .options(selectinload(ReportPushTask.records))
        .where(ReportPushTask.id == task.id)
        .execution_options(populate_existing=True)
    )
    return _push_out(refreshed or task)


def _get_push_task(db: DbSession, task_id: int) -> ReportPushTask | None:
    return db.scalar(
        select(ReportPushTask)
        .options(selectinload(ReportPushTask.records))
        .where(ReportPushTask.id == task_id)
        .execution_options(populate_existing=True)
    )


def _reset_stale_push(db: DbSession, task: ReportPushTask) -> ReportPushTask | None:
    cutoff = utcnow() - PUSH_STALE_AFTER
    if task.status != ReportPushStatus.推送中 or task.updated_at >= cutoff:
        return task
    result = db.execute(
        update(ReportPushTask)
        .where(
            ReportPushTask.id == task.id,
            ReportPushTask.status == ReportPushStatus.推送中,
            ReportPushTask.updated_at < cutoff,
        )
        .values(status=ReportPushStatus.失败, updated_at=utcnow())
        .execution_options(synchronize_session=False)
    )
    if result.rowcount == 1:
        db.add(
            ReportPushRecord(
                push_task_id=task.id,
                channel=task.channel,
                target_object=_mask_open_id(task.target_object),
                recipient_type=task.recipient_type,
                message_summary="推送超时自动复位",
                status=ReportPushRecordStatus.失败,
                error_code="PUSH_TIMEOUT_RESET",
                error_message="推送超时自动复位",
                response_snapshot={"code": "PUSH_TIMEOUT_RESET", "msg": "推送超时自动复位"},
                attempt_no=(task.retry_count or 0) + 1,
            )
        )
        db.commit()
    else:
        db.rollback()
    return _get_push_task(db, task.id)


def _safe_exception_summary(exc: Exception, open_ids: list[str]) -> str:
    return _redact_text(f"{type(exc).__name__}: {exc}", open_ids)[:2000]


def _safe_response_data(value: object, open_ids: list[str]) -> object:
    if isinstance(value, dict):
        return {key: _safe_response_data(item, open_ids) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_response_data(item, open_ids) for item in value]
    if isinstance(value, str):
        return _redact_text(value, open_ids)
    return value


def _redact_text(value: str, open_ids: list[str]) -> str:
    summary = re.sub(
        r"Bearer\s+\S+", "Bearer ***REDACTED***", value, flags=re.IGNORECASE
    )
    for value in (settings.feishu_app_secret, *open_ids):
        if value:
            summary = summary.replace(value, _mask_open_id(value) if value.startswith("ou_") else "***REDACTED***")
    return summary


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
