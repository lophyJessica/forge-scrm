"""日志配置。红线：任何密钥/密码不得进入日志（见 app/core/logging.py 的脱敏过滤器）。"""

import logging
import re
import sys

from app.core.config import settings

_SENSITIVE_PATTERNS = [
    re.compile(r"(sk-[A-Za-z0-9]{8,})"),
    re.compile(r"(?i)(authorization\s*[:=]\s*)(bearer\s+)?\S+"),
    re.compile(r"(?i)((?:api[_-]?key|token|secret|password|password_hash)\s*[\"']?\s*[:=]\s*[\"']?)([^\s,\"'}]+)"),
]


class RedactFilter(logging.Filter):
    """在日志落地前抹掉可能出现的凭证明文（对应 MVP 验收 S05）。"""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - 防御性
            return True
        redacted = message
        for pattern in _SENSITIVE_PATTERNS:
            if pattern.groups == 1:
                redacted = pattern.sub("***REDACTED***", redacted)
            else:
                redacted = pattern.sub(lambda m: f"{m.group(1)}***REDACTED***", redacted)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def setup_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    )
    handler.addFilter(RedactFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for noisy in ("uvicorn.access", "uvicorn.error", "sqlalchemy.engine"):
        logging.getLogger(noisy).addFilter(RedactFilter())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
