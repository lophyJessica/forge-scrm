"""自动采集执行器。

当前只实现可配置的公开 HTTP/JSON 拉取适配器。视频号、小红书等平台的
官方接口、授权方式和字段仍需实测，不能在没有真实来源的情况下生成假数据。
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BizError, not_found
from app.models.base import utcnow
from app.models.phase2 import (
    BenchmarkAccount,
    CollectionRecord,
    CollectionRecordStatus,
    CollectionResult,
    CollectionTask,
    CollectionTaskStatus,
)


class CollectionAdapterError(Exception):
    """单个账号采集失败，不应中断同一任务的其他账号。"""

    def __init__(self, message: str, code: str = "COLLECTION_FAILED", http_status: int | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


@dataclass(frozen=True)
class CollectionFetch:
    """适配器返回的真实来源响应。"""

    source_url: str
    raw_content: str
    structured_data: dict[str, Any] | None
    item_count: int
    http_status: int


class BenchmarkAccountAdapter(Protocol):
    """对标账号适配器接口。

    平台适配器应使用平台允许的官方 API 或授权接口。当前通用适配器只拉取
    benchmark_account.profile_url 指向的公开 HTTP/JSON 内容；平台接口适配器
    的具体实现和字段映射标记为 TODO(待实测)。
    """

    def fetch(self, account: BenchmarkAccount, task: CollectionTask) -> CollectionFetch:
        ...


class GenericPublicHttpAdapter:
    """拉取账号配置的公开 URL，不绕过登录、验证码或风控。"""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def fetch(self, account: BenchmarkAccount, task: CollectionTask) -> CollectionFetch:
        url = _public_url(account, task)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise CollectionAdapterError(
                "未配置可采集的公开 HTTP/HTTPS URL；平台官方接口仍需实测",
                code="PUBLIC_URL_INVALID",
            )

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(url, headers={"Accept": "application/json, text/plain;q=0.9"})
        except httpx.HTTPError as exc:
            raise CollectionAdapterError(f"公开来源不可达：{exc}", code="SOURCE_UNREACHABLE") from exc

        if response.status_code >= 400:
            raise CollectionAdapterError(
                f"公开来源返回 HTTP {response.status_code}",
                code="SOURCE_HTTP_ERROR",
                http_status=response.status_code,
            )

        raw_content = response.text
        if not raw_content.strip():
            raise CollectionAdapterError("公开来源返回空内容", code="EMPTY_RESPONSE", http_status=response.status_code)

        structured_data = None
        try:
            parsed_body = response.json()
            if isinstance(parsed_body, dict):
                structured_data = parsed_body
            else:
                structured_data = {"items": parsed_body}
        except ValueError:
            # 纯文本也是来源原始事实，不能伪造结构化数据。
            structured_data = None

        item_count = _item_count(structured_data)
        return CollectionFetch(
            source_url=str(response.url),
            raw_content=raw_content,
            structured_data=structured_data,
            item_count=item_count,
            http_status=response.status_code,
        )


def get_adapter(task: CollectionTask, account: BenchmarkAccount) -> BenchmarkAccountAdapter:
    """解析适配器。

    TODO(待实测)：按 platform 接入官方 API/授权适配器。未完成实测前统一使用
    公开 URL 适配器，要求账号配置 profile_url 或 scope_config.public_urls。
    """

    adapter_name = (task.scope_config or {}).get("adapter", "generic_http")
    if adapter_name != "generic_http":
        raise CollectionAdapterError(
            f"采集适配器「{adapter_name}」尚未实测或实现",
            code="ADAPTER_NOT_AVAILABLE",
        )
    return GenericPublicHttpAdapter()


def execute_task(db: Session, task_id: int, *, is_retry: bool = False) -> CollectionTask:
    """执行一次采集任务并同步返回最终任务状态。"""

    task = db.get(CollectionTask, task_id)
    if task is None:
        raise not_found("采集任务")
    if task.status not in {CollectionTaskStatus.pending, CollectionTaskStatus.failed}:
        raise BizError(
            f"当前状态「{task.status.value}」不可执行（仅 pending/failed 可执行）",
            code=409,
        )

    account_ids = _account_ids(task.scope_config)
    if not account_ids:
        raise BizError("scope_config 必须包含至少一个 benchmark_account_ids", code=400)
    if task.scope_type != "benchmark_account":
        raise BizError(f"暂不支持采集范围：{task.scope_type}", code=400)

    accounts = list(
        db.scalars(select(BenchmarkAccount).where(BenchmarkAccount.id.in_(account_ids))).all()
    )
    account_map = {account.id: account for account in accounts}
    missing_ids = [account_id for account_id in account_ids if account_id not in account_map]
    if missing_ids:
        raise BizError(f"对标账号不存在：{missing_ids}", code=400)
    disabled = [account.account_identifier for account in accounts if not account.enabled]
    if disabled:
        raise BizError(f"对标账号已停用，不能开始采集：{', '.join(disabled)}", code=400)

    task.status = CollectionTaskStatus.running
    task.started_at = utcnow()
    task.finished_at = None
    task.error_message = None
    task.total_count = len(account_ids)
    task.success_count = 0
    task.failure_count = 0
    db.commit()

    errors: list[str] = []
    for account_id in account_ids:
        account = account_map[account_id]
        previous_success = _successful_record(db, task.id, account.id)
        if previous_success is not None:
            task.success_count += 1
            continue

        record = CollectionRecord(
            task_id=task.id,
            benchmark_account_id=account.id,
            source_type="benchmark_account",
            source_url=_public_url(account, task, required=False),
            status=CollectionRecordStatus.running,
            attempt_no=_next_attempt_no(db, task.id, account.id),
            requested_at=utcnow(),
        )
        db.add(record)
        db.flush()
        try:
            adapter = get_adapter(task, account)
            fetched = adapter.fetch(account, task)
            record.status = CollectionRecordStatus.success
            record.completed_at = utcnow()
            record.raw_response = fetched.raw_content
            record.source_url = fetched.source_url
            record.http_status = fetched.http_status
            record.item_count = fetched.item_count
            record.retryable = False
            db.add(
                CollectionResult(
                    record_id=record.id,
                    task_id=task.id,
                    benchmark_account_id=account.id,
                    business_object="对标账号",
                    platform=account.platform,
                    account_identifier=account.account_identifier,
                    is_benchmark=account.benchmark_flag,
                    source_url=fetched.source_url,
                    raw_content=fetched.raw_content,
                    structured_data=fetched.structured_data,
                    collected_at=utcnow(),
                    window_start=task.time_window_start,
                    window_end=task.time_window_end,
                    is_ai_product=False,
                )
            )
            account.last_collected_at = utcnow()
            task.success_count += 1
        except CollectionAdapterError as exc:
            _mark_record_failed(record, exc)
            errors.append(f"{account.account_identifier}：{exc.message}")
        except Exception as exc:  # noqa: BLE001 - 单账号隔离，继续执行其他账号
            failure = CollectionAdapterError(f"采集执行异常：{exc}", code="COLLECTION_INTERNAL_ERROR")
            _mark_record_failed(record, failure)
            errors.append(f"{account.account_identifier}：{failure.message}")
        finally:
            db.commit()

    task.failure_count = task.total_count - task.success_count
    task.finished_at = utcnow()
    task.error_message = "；".join(errors) if errors else None
    if task.success_count == 0:
        task.status = CollectionTaskStatus.failed
    elif task.failure_count:
        task.status = CollectionTaskStatus.partial_success
    else:
        task.status = CollectionTaskStatus.success
    db.commit()
    db.refresh(task)
    return task


def retry_task(db: Session, task_id: int) -> CollectionTask:
    """任务级重试；保留旧记录和结果，只增加任务尝试次数。"""

    task = db.get(CollectionTask, task_id)
    if task is None:
        raise not_found("采集任务")
    if task.status != CollectionTaskStatus.failed:
        raise BizError("只有 failed 状态的采集任务可重试", code=409)
    task.retry_count += 1
    db.commit()
    return execute_task(db, task_id, is_retry=True)


def retry_record(db: Session, record_id: int) -> CollectionRecord:
    """Retry one failed record without creating a second successful result."""

    record = db.get(CollectionRecord, record_id)
    if record is None:
        raise not_found("采集记录")
    if record.status != CollectionRecordStatus.failed or not record.retryable:
        raise BizError("只有可重试的失败记录可以重试", code=409)

    task = db.get(CollectionTask, record.task_id)
    if task is None:
        raise not_found("采集任务")
    if task.status == CollectionTaskStatus.running:
        raise BizError("采集任务正在执行，请稍后再试", code=409)
    if record.benchmark_account_id is None:
        raise BizError("采集记录缺少对标账号，无法重试", code=400)
    account = db.get(BenchmarkAccount, record.benchmark_account_id)
    if account is None:
        raise not_found("对标账号")
    if not account.enabled:
        raise BizError("对标账号已停用，不能重试", code=400)
    if _successful_record(db, task.id, account.id) is not None:
        raise BizError("该账号已有成功采集结果，不重复生成", code=409)

    previous_record = record
    previous_record.retryable = False
    record = CollectionRecord(
        task_id=task.id,
        benchmark_account_id=account.id,
        source_type=previous_record.source_type,
        source_url=previous_record.source_url,
        status=CollectionRecordStatus.running,
        attempt_no=previous_record.attempt_no + 1,
        requested_at=utcnow(),
    )
    db.add(record)
    db.flush()
    task.status = CollectionTaskStatus.running
    task.started_at = utcnow()
    task.finished_at = None
    db.commit()

    try:
        fetched = get_adapter(task, account).fetch(account, task)
        record.status = CollectionRecordStatus.success
        record.completed_at = utcnow()
        record.raw_response = fetched.raw_content
        record.source_url = fetched.source_url
        record.http_status = fetched.http_status
        record.item_count = fetched.item_count
        db.add(
            CollectionResult(
                record_id=record.id,
                task_id=task.id,
                benchmark_account_id=account.id,
                business_object="对标账号",
                platform=account.platform,
                account_identifier=account.account_identifier,
                is_benchmark=account.benchmark_flag,
                source_url=fetched.source_url,
                raw_content=fetched.raw_content,
                structured_data=fetched.structured_data,
                collected_at=utcnow(),
                window_start=task.time_window_start,
                window_end=task.time_window_end,
                is_ai_product=False,
            )
        )
        account.last_collected_at = utcnow()
    except CollectionAdapterError as exc:
        _mark_record_failed(record, exc)
    except Exception as exc:  # noqa: BLE001 - 记录级隔离
        _mark_record_failed(record, CollectionAdapterError(f"采集执行异常：{exc}", code="COLLECTION_INTERNAL_ERROR"))
    finally:
        db.commit()

    _refresh_task_status(db, task)
    return record


def _account_ids(scope_config: dict[str, Any] | None) -> list[int]:
    config = scope_config or {}
    raw_ids = config.get("benchmark_account_ids", config.get("account_ids", []))
    if not isinstance(raw_ids, list):
        return []
    result: list[int] = []
    for raw_id in raw_ids:
        try:
            account_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if account_id not in result:
            result.append(account_id)
    return result


def _public_url(account: BenchmarkAccount, task: CollectionTask, *, required: bool = True) -> str | None:
    urls = (task.scope_config or {}).get("public_urls", {})
    url = urls.get(str(account.id), urls.get(account.account_identifier)) if isinstance(urls, dict) else None
    url = url or account.profile_url
    if required and not url:
        raise CollectionAdapterError("账号未配置公开 URL；平台 API 尚未实测", code="PUBLIC_URL_MISSING")
    return url


def _item_count(structured_data: dict[str, Any] | None) -> int:
    if not structured_data:
        return 1
    items = structured_data.get("items")
    if isinstance(items, list):
        return len(items)
    return 1


def _successful_record(db: Session, task_id: int, account_id: int) -> CollectionRecord | None:
    stmt = (
        select(CollectionRecord)
        .where(
            CollectionRecord.task_id == task_id,
            CollectionRecord.benchmark_account_id == account_id,
            CollectionRecord.status == CollectionRecordStatus.success,
        )
        .order_by(CollectionRecord.id.desc())
    )
    return db.scalars(stmt).first()


def _refresh_task_status(db: Session, task: CollectionTask) -> None:
    """Recompute task counters from the latest successful account records."""

    account_ids = _account_ids(task.scope_config)
    success_ids = set(
        db.scalars(
            select(CollectionRecord.benchmark_account_id)
            .where(
                CollectionRecord.task_id == task.id,
                CollectionRecord.status == CollectionRecordStatus.success,
            )
        ).all()
    )
    success_count = len({account_id for account_id in success_ids if account_id is not None})
    task.total_count = len(account_ids)
    task.success_count = success_count
    task.failure_count = max(task.total_count - success_count, 0)
    task.finished_at = utcnow()
    task.status = (
        CollectionTaskStatus.failed
        if success_count == 0
        else CollectionTaskStatus.partial_success
        if task.failure_count
        else CollectionTaskStatus.success
    )
    db.commit()
    db.refresh(task)


def _next_attempt_no(db: Session, task_id: int, account_id: int) -> int:
    stmt = select(CollectionRecord).where(
        CollectionRecord.task_id == task_id,
        CollectionRecord.benchmark_account_id == account_id,
    ).order_by(CollectionRecord.attempt_no.desc())
    previous = db.scalars(stmt).first()
    return (previous.attempt_no + 1) if previous else 1


def _mark_record_failed(record: CollectionRecord, error: CollectionAdapterError) -> None:
    record.status = CollectionRecordStatus.failed
    record.completed_at = utcnow()
    record.http_status = error.http_status
    record.error_code = error.code
    record.error_message = error.message
    record.retryable = True
