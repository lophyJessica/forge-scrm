"""CSV/TXT 导入工具（D-T2 固定模板 + 列名映射；D-T4 原文件存本地磁盘）。"""

import csv
import io
import re
from datetime import datetime
from pathlib import Path

from app.core.config import settings

_SAFE_NAME = re.compile(r"[^A-Za-z0-9_.\-]")


def sniff_rows(raw: bytes) -> list[dict[str, str]]:
    """解析 CSV/TXT 为字典行列表。

    - 支持 UTF-8（含 BOM）与 GBK；
    - 分隔符自动识别逗号 / 制表符（TXT 常见）。
    """
    text: str | None = None
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("文件编码无法识别，请使用 UTF-8 或 GBK 编码")

    text = text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not text:
        raise ValueError("文件内容为空")

    header_line = text.split("\n", 1)[0]
    delimiter = "\t" if header_line.count("\t") > header_line.count(",") else ","

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("缺少表头行")
    rows = []
    for row in reader:
        rows.append({(k or "").strip(): (v or "").strip() for k, v in row.items()})
    return rows


def check_headers(rows_fieldnames: list[str], required: list[str]) -> list[str]:
    """返回缺失的必需列名。"""
    present = {f.strip() for f in rows_fieldnames}
    return [c for c in required if c not in present]


def read_headers(raw: bytes) -> list[str]:
    text = None
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("文件编码无法识别，请使用 UTF-8 或 GBK 编码")
    header_line = text.replace("\r\n", "\n").split("\n", 1)[0]
    delimiter = "\t" if header_line.count("\t") > header_line.count(",") else ","
    return [h.strip().lstrip("﻿") for h in header_line.split(delimiter)]


def store_original(raw: bytes, filename: str, prefix: str) -> str:
    """把导入原文件落到 backend/data/csv/（D-T4），返回相对路径用于追溯。"""
    safe = _SAFE_NAME.sub("_", Path(filename).name) or "upload.csv"
    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    target = settings.csv_path / f"{prefix}_{stamp}_{safe}"
    target.write_bytes(raw)
    return str(target.relative_to(settings.data_path.parent))


def build_template(headers: list[str], sample_rows: list[list[str]]) -> bytes:
    """生成带 BOM 的 UTF-8 模板，Excel 直接打开不乱码。"""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in sample_rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8-sig")
