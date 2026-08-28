"""飞书企业自建应用消息推送。凭据与 token 仅驻留进程内存。"""

import json
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from collections.abc import Callable
from typing import Any

import httpx

from app.core.config import settings

TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"
TOKEN_INVALID_CODES = {99991663, 99991661}
HTTP_TIMEOUT = 10.0
CARD_MAX_BYTES = 28 * 1024
TRUNCATION_NOTICE = "正文超长已截断，完整内容请登录系统查看"
COLLAPSED_PREVIEW_NOTICE = "正文已折叠展示，完整内容以系统为准"
CARD_V2_UNSUPPORTED_CODES = {99991672}

_token_lock = threading.Lock()
_cached_token: str | None = None
_cached_until = 0.0
_recent_tokens: list[str] = []


class FeishuPushError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)

    @property
    def summary(self) -> str:
        return json.dumps({"code": self.code, "msg": self.message}, ensure_ascii=False)


@dataclass(frozen=True)
class PushResult:
    ok: bool
    summary: str
    downgraded: bool = False


@dataclass(frozen=True)
class _SendAttempt:
    ok: bool
    summary: str
    http_status: int | None = None
    code: Any = None


def get_tenant_token(*, force_refresh: bool = False) -> str:
    """获取并缓存 tenant_access_token，过期前五分钟刷新。"""

    global _cached_token, _cached_until
    with _token_lock:
        now = time.monotonic()
        if not force_refresh and _cached_token and now < _cached_until:
            return _cached_token
        if not settings.feishu_app_id or not settings.feishu_app_secret:
            raise FeishuPushError("FEISHU_CONFIG_MISSING", "飞书应用凭据未配置")

        try:
            with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                response = client.post(
                    TOKEN_URL,
                    json={
                        "app_id": settings.feishu_app_id,
                        "app_secret": settings.feishu_app_secret,
                    },
                )
        except httpx.HTTPError as exc:
            raise FeishuPushError("FEISHU_TOKEN_NETWORK_ERROR", "飞书 token 请求失败") from exc

        body = _json_body(response)
        code = body.get("code")
        if response.status_code >= 400 or code != 0:
            raise FeishuPushError(str(code or response.status_code), _safe_msg(body))
        token = body.get("tenant_access_token")
        if not isinstance(token, str) or not token:
            raise FeishuPushError("FEISHU_TOKEN_INVALID_RESPONSE", "飞书 token 响应缺少 token")
        try:
            expires_in = int(body.get("expire") or 0)
        except (TypeError, ValueError):
            expires_in = 0
        _cached_token = token
        _recent_tokens[:] = [token, *[item for item in _recent_tokens if item != token]][:2]
        _cached_until = now + max(0, expires_in - 300)
        return token


def send_report_card(
    open_id: str,
    title: str,
    generated_at: datetime | str | None,
    digest: str,
    report_body: str,
    overview: str | None = None,
) -> PushResult:
    """优先发送卡片 2.0；组件不支持时仅降级重试一次旧版卡片。"""

    result = _send_card_to(
        open_id, _report_card_v2(title, generated_at, digest, report_body, overview)
    )
    if result.ok:
        return PushResult(True, result.summary)
    if not _should_fallback_to_legacy(result):
        return PushResult(False, result.summary)

    fallback = _send_card_to(
        open_id, _report_card_legacy(title, generated_at, digest, report_body, overview)
    )
    return PushResult(fallback.ok, fallback.summary, downgraded=True)


def _send_card_to(open_id: str, card: dict[str, Any]) -> _SendAttempt:
    payload = {
        "receive_id": open_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False),
    }
    for attempt in range(2):
        try:
            token = get_tenant_token(force_refresh=attempt > 0)
        except FeishuPushError as exc:
            return _SendAttempt(False, exc.summary, code=exc.code)
        try:
            with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                response = client.post(
                    MESSAGE_URL,
                    params={"receive_id_type": "open_id"},
                    headers={"Authorization": f"Bearer {token}"},
                    json=payload,
                )
        except httpx.HTTPError:
            return _SendAttempt(
                False,
                json.dumps(
                    {"code": "FEISHU_SEND_NETWORK_ERROR", "msg": "飞书消息请求失败"},
                    ensure_ascii=False,
                ),
                code="FEISHU_SEND_NETWORK_ERROR",
            )

        body = _json_body(response)
        summary = _response_summary(response.status_code, body)
        code = body.get("code")
        if response.status_code < 400 and code == 0:
            return _SendAttempt(True, summary, response.status_code, code)
        if code in TOKEN_INVALID_CODES and attempt == 0:
            continue
        return _SendAttempt(False, summary, response.status_code, code)
    return _SendAttempt(
        False,
        json.dumps(
            {"code": "FEISHU_SEND_FAILED", "msg": "飞书消息发送失败"},
            ensure_ascii=False,
        ),
        code="FEISHU_SEND_FAILED",
    )


def _report_card_v2(
    title: str,
    generated_at: datetime | str | None,
    digest: str,
    report_body: str,
    overview: str | None = None,
) -> dict[str, Any]:
    generated_text = _generated_text(generated_at)
    body = _to_lark_md(report_body) or "暂无正文"

    def build(body_text: str) -> dict[str, Any]:
        elements: list[dict[str, Any]] = [
            {
                "tag": "markdown",
                "content": f"**生成时间**\n{generated_text}",
            },
            {
                "tag": "markdown",
                "content": f"**摘要**\n{(digest or '—')[:800]}",
            },
        ]
        if overview:
            elements.append(
                {
                    "tag": "markdown",
                    "content": f"**数据概览**\n{overview}",
                }
            )
        elements.append(
            {
                "tag": "collapsible_panel",
                "expanded": False,
                "direction": "vertical",
                "vertical_spacing": "8px",
                "padding": "8px 8px 8px 8px",
                "background_color": "grey",
                "header": {
                    "title": {"tag": "plain_text", "content": "报告正文（点击展开）"},
                    "background_color": "grey",
                },
                "border": {"color": "grey", "corner_radius": "5px"},
                "elements": [{"tag": "markdown", "content": body_text}],
            }
        )
        return {
            "schema": "2.0",
            "header": {
                "template": "purple",
                "title": {"tag": "plain_text", "content": title or "数据报告"},
            },
            "body": {"elements": elements},
        }

    return _fit_card_body(build, body)


def _report_card_legacy(
    title: str,
    generated_at: datetime | str | None,
    digest: str,
    report_body: str,
    overview: str | None = None,
) -> dict[str, Any]:
    generated_text = _generated_text(generated_at)
    body = (_to_lark_md(report_body) or "暂无正文")[:500].rstrip()
    body = f"{body}\n\n{COLLAPSED_PREVIEW_NOTICE}"

    def build(body_text: str) -> dict[str, Any]:
        elements: list[dict[str, Any]] = [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**生成时间**\n{generated_text}"},
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**摘要**\n{(digest or '—')[:800]}"},
            },
        ]
        if overview:
            elements.append(
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"**数据概览**\n{overview}"},
                }
            )
        elements.append(
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**报告正文**\n\n{body_text}"},
            }
        )
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "purple",
                "title": {"tag": "plain_text", "content": title or "数据报告"},
            },
            "elements": elements,
        }

    return _fit_card_body(build, body)


def _fit_card_body(
    build: Callable[[str], dict[str, Any]], body: str
) -> dict[str, Any]:
    card = build(body)
    if _card_size(card) < CARD_MAX_BYTES:
        return card

    low, high = 0, len(body)
    best = build(TRUNCATION_NOTICE)
    while low <= high:
        middle = (low + high) // 2
        prefix = body[:middle].rstrip()
        candidate_body = f"{prefix}\n\n{TRUNCATION_NOTICE}" if prefix else TRUNCATION_NOTICE
        candidate = build(candidate_body)
        if _card_size(candidate) < CARD_MAX_BYTES:
            best = candidate
            low = middle + 1
        else:
            high = middle - 1
    return best


def _generated_text(generated_at: datetime | str | None) -> str:
    if isinstance(generated_at, datetime):
        return generated_at.strftime("%Y-%m-%d %H:%M:%S")
    return str(generated_at or "—")


def _should_fallback_to_legacy(result: _SendAttempt) -> bool:
    if result.code in TOKEN_INVALID_CODES:
        return False
    return result.http_status == 400 or result.code in CARD_V2_UNSUPPORTED_CODES


def _to_lark_md(content: str) -> str:
    lines: list[str] = []
    for raw_line in (content or "").splitlines():
        line = raw_line.rstrip()
        heading = re.match(r"^#{1,6}\s+(.+)$", line)
        if heading:
            lines.append(f"**{heading.group(1).strip()}**")
            continue

        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) > 1:
            compact_cells = [cell.replace(" ", "") for cell in cells]
            if all(re.fullmatch(r":?-{3,}:?", cell) for cell in compact_cells):
                continue
            lines.append(f"- {' / '.join(cells)}")
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _card_size(card: dict[str, Any]) -> int:
    return len(json.dumps(card, ensure_ascii=False).encode("utf-8"))


def _json_body(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {"code": response.status_code, "msg": "飞书返回非 JSON 响应"}
    return body if isinstance(body, dict) else {"code": response.status_code, "msg": "飞书响应格式异常"}


def _safe_msg(body: dict[str, Any]) -> str:
    message = str(body.get("msg") or body.get("message") or "飞书请求失败")
    for credential in (settings.feishu_app_secret, *_recent_tokens):
        if credential:
            message = message.replace(credential, "***REDACTED***")
    return message[:500]


def _response_summary(http_status: int, body: dict[str, Any]) -> str:
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    summary = {
        "http_status": http_status,
        "code": body.get("code"),
        "msg": _safe_msg(body),
    }
    message_id = data.get("message_id")
    if message_id:
        summary["message_id"] = str(message_id)
    return json.dumps(summary, ensure_ascii=False)
