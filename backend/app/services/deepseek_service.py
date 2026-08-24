"""DeepSeek 调用封装。

红线：API Key 只能来自环境变量 DEEPSEEK_API_KEY，绝不硬编码，也绝不写入日志。
能力：chat/completions（JSON 输出）+ JSON schema 校验 + 失败重试 3 次指数退避 + 原始响应留档。
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import httpx

from app.core.config import settings
from app.core.exceptions import BizError
from app.core.logging import get_logger

logger = get_logger(__name__)


class DeepSeekError(Exception):
    """DeepSeek 调用或结构化校验失败；raw 保留原始响应用于留档（S03/S04）。"""

    def __init__(self, message: str, raw: str = ""):
        super().__init__(message)
        self.message = message
        self.raw = raw


def archive_raw(raw: str, prefix: str) -> str:
    """AI 原始响应留档到 backend/data/ai_raw/（D-T4），返回相对路径。"""
    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    target: Path = settings.ai_raw_path / f"{prefix}_{stamp}.json"
    target.write_text(raw or "", encoding="utf-8")
    return str(target.relative_to(settings.data_path.parent))


def _extract_json(text: str) -> Any:
    """从模型输出中提取 JSON（兼容 ```json 包裹）。"""
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = min(
            [i for i in (cleaned.find("{"), cleaned.find("[")) if i >= 0] or [-1]
        )
        end = max(cleaned.rfind("}"), cleaned.rfind("]"))
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def chat_json(
    system_prompt: str,
    user_prompt: str,
    validator: Callable[[Any], Any] | None = None,
    temperature: float = 0.7,
    max_retry: int | None = None,
) -> tuple[Any, str]:
    """调用 DeepSeek 并返回 (结构化结果, 原始响应文本)。

    失败（网络 / 非 2xx / JSON 解析 / schema 校验）时重试，最多 max_retry 次，指数退避。
    全部失败抛 DeepSeekError，其中 raw 为最后一次原始响应（用于留档与重试追溯）。
    """
    if not settings.deepseek_api_key:
        raise BizError("DeepSeek API Key 未配置：请在 backend/.env 设置 DEEPSEEK_API_KEY")

    retries = settings.deepseek_max_retry if max_retry is None else max_retry
    url = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }

    last_raw = ""
    last_error = ""
    for attempt in range(1, retries + 1):
        try:
            with httpx.Client(timeout=settings.deepseek_timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
            last_raw = resp.text
            if resp.status_code >= 400:
                # 只记录状态码，不记录 header/密钥
                raise DeepSeekError(f"DeepSeek 返回 HTTP {resp.status_code}", resp.text)
            body = resp.json()
            content = body["choices"][0]["message"]["content"]
            last_raw = content
            parsed = _extract_json(content)
            if validator is not None:
                parsed = validator(parsed)
            logger.info("DeepSeek 调用成功（第 %s 次尝试）", attempt)
            return parsed, content
        except Exception as exc:  # noqa: BLE001 - 统一重试
            last_error = str(exc)
            logger.warning("DeepSeek 第 %s/%s 次尝试失败：%s", attempt, retries, last_error)
            if attempt < retries:
                time.sleep(2 ** (attempt - 1))

    raise DeepSeekError(f"DeepSeek 调用失败（已重试 {retries} 次）：{last_error}", last_raw)
