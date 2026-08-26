"""二期自动采集与研究助手 CRUD 及执行入口。"""

from datetime import datetime

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.core.exceptions import BizError, not_found
from app.models.phase2 import (
    BenchmarkAccount,
    CollectionRecord,
    CollectionResult,
    CollectionTask,
    CollectionTaskStatus,
    ResearchReference,
    ResearchReport,
    ResearchTask,
    ResearchTaskStatus,
)
from app.models.base import utcnow
from app.schemas.common import OkResult, PageResult
from app.schemas.phase2 import (
    BenchmarkAccountCreate,
    BenchmarkAccountOut,
    BenchmarkAccountUpdate,
    CollectionRecordOut,
    CollectionResultOut,
    CollectionTaskCreate,
    CollectionTaskOut,
    CollectionTaskUpdate,
    ResearchReferenceOut,
    ResearchReportOut,
    ResearchTaskCreate,
    ResearchTaskOut,
    ResearchTaskUpdate,
)
from app.services import collection_executor, research_executor

router = APIRouter(prefix="/api/v1", tags=["二期骨架"])


def _task_no(prefix: str) -> str:
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


# ==================== 自动采集：对标账号 ====================

@router.get(
    "/benchmark-accounts",
    response_model=PageResult[BenchmarkAccountOut],
    summary="对标账号列表（骨架）",
)
def list_benchmark_accounts(
    _: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    platform: str | None = None,
    enabled: bool | None = None,
    keyword: str | None = None,
) -> PageResult[BenchmarkAccountOut]:
    stmt = select(BenchmarkAccount)
    if platform:
        stmt = stmt.where(BenchmarkAccount.platform == platform)
    if enabled is not None:
        stmt = stmt.where(BenchmarkAccount.enabled.is_(enabled))
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            BenchmarkAccount.account_identifier.like(like)
            | BenchmarkAccount.account_name.like(like)
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(BenchmarkAccount.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PageResult(
        total=total,
        page=page,
        page_size=page_size,
        items=[BenchmarkAccountOut.model_validate(row) for row in rows],
    )


@router.post(
    "/benchmark-accounts",
    response_model=BenchmarkAccountOut,
    summary="创建对标账号（骨架）",
)
def create_benchmark_account(
    payload: BenchmarkAccountCreate, current_user: CurrentUser, db: DbSession
) -> BenchmarkAccountOut:
    row = BenchmarkAccount(
        **payload.model_dump(),
        created_by=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return BenchmarkAccountOut.model_validate(row)


@router.get(
    "/benchmark-accounts/{account_id}",
    response_model=BenchmarkAccountOut,
    summary="对标账号详情（骨架）",
)
def get_benchmark_account(account_id: int, _: CurrentUser, db: DbSession) -> BenchmarkAccountOut:
    row = db.get(BenchmarkAccount, account_id)
    if not row:
        raise not_found("对标账号")
    return BenchmarkAccountOut.model_validate(row)


@router.put(
    "/benchmark-accounts/{account_id}",
    response_model=BenchmarkAccountOut,
    summary="更新对标账号（骨架）",
)
def update_benchmark_account(
    account_id: int,
    payload: BenchmarkAccountUpdate,
    _: CurrentUser,
    db: DbSession,
) -> BenchmarkAccountOut:
    row = db.get(BenchmarkAccount, account_id)
    if not row:
        raise not_found("对标账号")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return BenchmarkAccountOut.model_validate(row)


@router.delete(
    "/benchmark-accounts/{account_id}",
    response_model=OkResult,
    summary="删除对标账号（骨架）",
)
def delete_benchmark_account(account_id: int, _: CurrentUser, db: DbSession) -> OkResult:
    row = db.get(BenchmarkAccount, account_id)
    if not row:
        raise not_found("对标账号")
    if db.scalar(select(func.count()).select_from(CollectionRecord).where(CollectionRecord.benchmark_account_id == account_id)):
        raise BizError("该对标账号已有采集记录，不能删除；可更新为停用")
    db.delete(row)
    db.commit()
    return OkResult(message="对标账号已删除")


# ==================== 自动采集：任务 ====================

@router.get(
    "/collection-tasks",
    response_model=PageResult[CollectionTaskOut],
    summary="采集任务列表（骨架）",
)
def list_collection_tasks(
    _: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: CollectionTaskStatus | None = None,
) -> PageResult[CollectionTaskOut]:
    stmt = select(CollectionTask)
    if status is not None:
        stmt = stmt.where(CollectionTask.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(CollectionTask.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PageResult(
        total=total,
        page=page,
        page_size=page_size,
        items=[CollectionTaskOut.model_validate(row) for row in rows],
    )


@router.post(
    "/collection-tasks",
    response_model=CollectionTaskOut,
    summary="创建采集任务（不执行）",
)
def create_collection_task(
    payload: CollectionTaskCreate, current_user: CurrentUser, db: DbSession
) -> CollectionTaskOut:
    task_no = payload.task_no or _task_no("CT")
    if db.scalar(select(CollectionTask.id).where(CollectionTask.task_no == task_no)):
        raise BizError("采集任务编号已存在")
    task = CollectionTask(
        task_no=task_no,
        trigger_type=payload.trigger_type,
        scope_type=payload.scope_type,
        scope_config=payload.scope_config,
        time_window_start=payload.time_window_start,
        time_window_end=payload.time_window_end,
        status=CollectionTaskStatus.pending,
        requested_by=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return CollectionTaskOut.model_validate(task)


@router.get(
    "/collection-tasks/{task_id}",
    response_model=CollectionTaskOut,
    summary="采集任务详情（骨架）",
)
def get_collection_task(task_id: int, _: CurrentUser, db: DbSession) -> CollectionTaskOut:
    task = db.get(CollectionTask, task_id)
    if not task:
        raise not_found("采集任务")
    return CollectionTaskOut.model_validate(task)


@router.put(
    "/collection-tasks/{task_id}",
    response_model=CollectionTaskOut,
    summary="更新采集任务配置（骨架）",
)
def update_collection_task(
    task_id: int,
    payload: CollectionTaskUpdate,
    _: CurrentUser,
    db: DbSession,
) -> CollectionTaskOut:
    task = db.get(CollectionTask, task_id)
    if not task:
        raise not_found("采集任务")
    if task.status != CollectionTaskStatus.pending:
        raise BizError("只有 pending 状态的采集任务可修改")
    data = payload.model_dump(exclude_unset=True)
    if "time_window_start" in data and "time_window_end" not in data:
        if data["time_window_start"] > task.time_window_end:
            raise BizError("时间窗结束不能早于开始")
    if "time_window_end" in data and "time_window_start" not in data:
        if data["time_window_end"] < task.time_window_start:
            raise BizError("时间窗结束不能早于开始")
    for key, value in data.items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return CollectionTaskOut.model_validate(task)


@router.delete(
    "/collection-tasks/{task_id}",
    response_model=OkResult,
    summary="删除采集任务（骨架）",
)
def delete_collection_task(task_id: int, _: CurrentUser, db: DbSession) -> OkResult:
    task = db.get(CollectionTask, task_id)
    if not task:
        raise not_found("采集任务")
    if task.status != CollectionTaskStatus.pending:
        raise BizError("只有 pending 状态的采集任务可删除")
    db.delete(task)
    db.commit()
    return OkResult(message="采集任务已删除")


@router.post(
    "/collection-tasks/{task_id}/execute",
    response_model=CollectionTaskOut,
    summary="触发采集任务",
)
def execute_collection_task(task_id: int, _: CurrentUser, db: DbSession) -> CollectionTaskOut:
    task = collection_executor.execute_task(db, task_id)
    return CollectionTaskOut.model_validate(task)


@router.post(
    "/collection-tasks/{task_id}/retry",
    response_model=CollectionTaskOut,
    summary="重试采集任务",
)
def retry_collection_task(task_id: int, _: CurrentUser, db: DbSession) -> CollectionTaskOut:
    task = collection_executor.retry_task(db, task_id)
    return CollectionTaskOut.model_validate(task)


# ==================== 自动采集：记录 / 结果 ====================

@router.get(
    "/collection-records",
    response_model=PageResult[CollectionRecordOut],
    summary="采集记录列表（骨架）",
)
def list_collection_records(
    _: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    task_id: int | None = None,
    status: str | None = None,
) -> PageResult[CollectionRecordOut]:
    stmt = select(CollectionRecord)
    if task_id is not None:
        stmt = stmt.where(CollectionRecord.task_id == task_id)
    if status:
        stmt = stmt.where(CollectionRecord.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(CollectionRecord.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PageResult(
        total=total,
        page=page,
        page_size=page_size,
        items=[CollectionRecordOut.model_validate(row) for row in rows],
    )


@router.get(
    "/collection-results",
    response_model=PageResult[CollectionResultOut],
    summary="采集结果列表（骨架）",
)
def list_collection_results(
    _: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    task_id: int | None = None,
    record_id: int | None = None,
    benchmark_account_id: int | None = None,
) -> PageResult[CollectionResultOut]:
    stmt = select(CollectionResult)
    if task_id is not None:
        stmt = stmt.where(CollectionResult.task_id == task_id)
    if record_id is not None:
        stmt = stmt.where(CollectionResult.record_id == record_id)
    if benchmark_account_id is not None:
        stmt = stmt.where(CollectionResult.benchmark_account_id == benchmark_account_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(CollectionResult.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PageResult(
        total=total,
        page=page,
        page_size=page_size,
        items=[CollectionResultOut.model_validate(row) for row in rows],
    )


# ==================== 研究助手：任务 ====================

@router.get(
    "/research-tasks",
    response_model=PageResult[ResearchTaskOut],
    summary="研究任务列表（骨架）",
)
def list_research_tasks(
    _: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: ResearchTaskStatus | None = None,
) -> PageResult[ResearchTaskOut]:
    stmt = select(ResearchTask)
    if status is not None:
        stmt = stmt.where(ResearchTask.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(ResearchTask.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PageResult(
        total=total,
        page=page,
        page_size=page_size,
        items=[ResearchTaskOut.model_validate(row) for row in rows],
    )


@router.post(
    "/research-tasks",
    response_model=ResearchTaskOut,
    summary="创建研究任务（不执行）",
)
def create_research_task(
    payload: ResearchTaskCreate, current_user: CurrentUser, db: DbSession
) -> ResearchTaskOut:
    task_no = payload.task_no or _task_no("RT")
    if db.scalar(select(ResearchTask.id).where(ResearchTask.task_no == task_no)):
        raise BizError("研究任务编号已存在")
    task = ResearchTask(
        task_no=task_no,
        topic=payload.topic,
        objective=payload.objective,
        scope_config=payload.scope_config,
        time_window_start=payload.time_window_start,
        time_window_end=payload.time_window_end,
        status=ResearchTaskStatus.pending,
        requested_by=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return ResearchTaskOut.model_validate(task)


@router.get(
    "/research-tasks/{task_id}",
    response_model=ResearchTaskOut,
    summary="研究任务详情（骨架）",
)
def get_research_task(task_id: int, _: CurrentUser, db: DbSession) -> ResearchTaskOut:
    task = db.get(ResearchTask, task_id)
    if not task:
        raise not_found("研究任务")
    return ResearchTaskOut.model_validate(task)


@router.put(
    "/research-tasks/{task_id}",
    response_model=ResearchTaskOut,
    summary="更新研究任务配置（骨架）",
)
def update_research_task(
    task_id: int,
    payload: ResearchTaskUpdate,
    _: CurrentUser,
    db: DbSession,
) -> ResearchTaskOut:
    task = db.get(ResearchTask, task_id)
    if not task:
        raise not_found("研究任务")
    if task.status != ResearchTaskStatus.pending:
        raise BizError("只有 pending 状态的研究任务可修改")
    data = payload.model_dump(exclude_unset=True)
    if "time_window_start" in data and "time_window_end" not in data:
        if task.time_window_end is not None and data["time_window_start"] > task.time_window_end:
            raise BizError("时间窗结束不能早于开始")
    if "time_window_end" in data and "time_window_start" not in data:
        if task.time_window_start is not None and data["time_window_end"] < task.time_window_start:
            raise BizError("时间窗结束不能早于开始")
    for key, value in data.items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return ResearchTaskOut.model_validate(task)


@router.delete(
    "/research-tasks/{task_id}",
    response_model=OkResult,
    summary="删除研究任务（骨架）",
)
def delete_research_task(task_id: int, _: CurrentUser, db: DbSession) -> OkResult:
    task = db.get(ResearchTask, task_id)
    if not task:
        raise not_found("研究任务")
    if task.status != ResearchTaskStatus.pending:
        raise BizError("只有 pending 状态的研究任务可删除")
    db.delete(task)
    db.commit()
    return OkResult(message="研究任务已删除")


@router.post(
    "/research-tasks/{task_id}/execute",
    response_model=ResearchTaskOut,
    summary="执行研究任务",
)
def execute_research_task(task_id: int, _: CurrentUser, db: DbSession) -> ResearchTaskOut:
    task = research_executor.execute_task(db, task_id)
    return ResearchTaskOut.model_validate(task)


@router.post(
    "/research-tasks/{task_id}/retry",
    response_model=ResearchTaskOut,
    summary="重试研究任务",
)
def retry_research_task(task_id: int, _: CurrentUser, db: DbSession) -> ResearchTaskOut:
    task = research_executor.retry_task(db, task_id)
    return ResearchTaskOut.model_validate(task)


# ==================== 研究助手：报告 / 引用 ====================

@router.get(
    "/research-reports/{report_id}",
    response_model=ResearchReportOut,
    summary="研究报告详情（骨架）",
)
def get_research_report(report_id: int, _: CurrentUser, db: DbSession) -> ResearchReportOut:
    report = db.get(ResearchReport, report_id)
    if not report:
        raise not_found("研究报告")
    return ResearchReportOut.model_validate(report)


@router.get(
    "/research-references",
    response_model=PageResult[ResearchReferenceOut],
    summary="研究引用关系列表（骨架）",
)
def list_research_references(
    _: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    report_id: int | None = None,
) -> PageResult[ResearchReferenceOut]:
    stmt = select(ResearchReference)
    if report_id is not None:
        stmt = stmt.where(ResearchReference.report_id == report_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(ResearchReference.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PageResult(
        total=total,
        page=page,
        page_size=page_size,
        items=[ResearchReferenceOut.model_validate(row) for row in rows],
    )
