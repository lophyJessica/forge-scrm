"""数据报告模块 TestClient 验收。

用法：cd backend && python scripts/selftest_reports.py
使用临时 SQLite，不污染开发库。
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

_TMP = tempfile.mkdtemp(prefix="forge_report_selftest_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/selftest.db"
os.environ["DATA_DIR"] = f"{_TMP}/data"
os.environ["DEEPSEEK_API_KEY"] = "TEST-STUB-KEY-NOT-REAL"
os.environ["JWT_SECRET"] = "selftest-secret"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.enums import AnalysisTaskStatus, AnalysisTaskType  # noqa: E402
from app.main import app  # noqa: E402
from app.models.analysis import AnalysisResult, AnalysisTask  # noqa: E402
from app.models.base import Base, utcnow  # noqa: E402
from app import models as _models  # noqa: E402,F401

Base.metadata.create_all(bind=engine)

RESULTS: list[tuple[str, str, str]] = []


def check(code: str, ok: bool, note: str = "") -> bool:
    RESULTS.append((code, "通过" if ok else "未通过", note))
    print(f"[{'PASS' if ok else 'FAIL'}] {code} {note}")
    return ok


client = TestClient(app)
client.__enter__()

r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
admin_token = r.json().get("access_token", "")
A = {"Authorization": f"Bearer {admin_token}"}
check("LOGIN", r.status_code == 200 and bool(admin_token), "管理员登录")

now = datetime.now()
period = {
    "period_start": (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S"),
    "period_end": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
}
empty_period = {
    "period_start": "2000-01-01T00:00:00",
    "period_end": "2000-01-07T23:59:59",
}

# ---------- 空源失败 ----------
r = client.post("/api/reports", headers=A, json={"report_type": "运营数据报告", **empty_period})
empty_id = r.json().get("id")
check("CREATE_EMPTY", r.status_code == 200 and r.json().get("generation_status") == "待生成", "空周期报告创建为待生成")

r = client.post(f"/api/reports/{empty_id}/generate", headers=A)
body = r.json()
check(
    "EMPTY_SOURCE_FAIL",
    r.status_code == 400 and "拒绝伪造" in str(body.get("detail", "")),
    f"空源生成失败 {r.status_code}: {body.get('detail')}",
)
r = client.get(f"/api/reports/{empty_id}", headers=A)
empty_row = r.json()
check(
    "EMPTY_STATUS",
    empty_row.get("generation_status") == "失败" and empty_row.get("error_code") == "EMPTY_SOURCE",
    "空源失败状态与错误码保留",
)

# ---------- 重试 409 / 计数 ----------
r = client.post(f"/api/reports/{empty_id}/retry", headers=A)
check(
    "RETRY_EMPTY_STILL_FAIL",
    r.status_code == 400,
    f"空源重试仍失败 {r.status_code}",
)
r = client.get(f"/api/reports/{empty_id}", headers=A)
check("RETRY_COUNT", r.json().get("retry_count") == 1, f"重试次数={r.json().get('retry_count')}")

# ---------- 有数据源：运营报告 200 ----------
r = client.post("/api/data-sources", headers=A, json={
    "name": "周报业务数据源",
    "collection_method": "手动录入",
    "business_object": "行业报告",
    "status": "启用",
})
source_id = r.json().get("id")
check("DATA_SOURCE", r.status_code == 200 and source_id, "创建业务数据源")

r = client.post("/api/raw-data", headers=A, json={
    "source_id": source_id,
    "raw_content": "本周视频号播放 1200，互动率 3.2%。",
    "structured": {"views": 1200, "engagement_rate": 0.032},
    "window_start": period["period_start"],
    "window_end": period["period_end"],
})
raw_id = r.json().get("id")
check("RAW_DATA", r.status_code == 200 and raw_id, "录入周期内业务原始数据")

db = SessionLocal()
try:
    created_by = client.get("/api/auth/me", headers=A).json().get("id") or 1
    task = AnalysisTask(
        name="周报分析任务",
        type=AnalysisTaskType.数据分析,
        output_schema={},
        status=AnalysisTaskStatus.已确认,
        created_by=created_by,
        created_at=utcnow(),
        retry_count=0,
    )
    db.add(task)
    db.flush()
    db.add(AnalysisResult(
        task_id=task.id,
        result_content={
            "effect": "互动率上升",
            "conclusion": "获客类内容表现更好",
            "suggestions": ["提高获客选题占比"],
        },
    ))
    db.commit()
    analysis_id = task.id
finally:
    db.close()

r = client.post("/api/reports", headers=A, json={"report_type": "运营数据报告", **period})
ops_id = r.json().get("id")
r = client.post(f"/api/reports/{ops_id}/generate", headers=A)
ops = r.json()
check(
    "OPS_GENERATE_200",
    r.status_code == 200 and ops.get("generation_status") == "已完成" and ops.get("is_ai_product") is True,
    f"运营报告生成 {r.status_code} status={ops.get('generation_status')}",
)
snapshot = ops.get("source_snapshot") or {}
source_types = {item.get("type") for item in (snapshot.get("sources") or [])}
check(
    "OPS_SOURCES",
    "raw_data" in source_types and "analysis_task" in source_types,
    f"来源快照包含 raw_data/analysis_task: {source_types}",
)
check("OPS_NO_FABRICATE", bool(ops.get("summary")) and bool(ops.get("content")), "摘要/正文来自聚合而非空造")

r = client.post(f"/api/reports/{ops_id}/retry", headers=A)
check("RETRY_409", r.status_code == 409, f"已完成报告重试应 409，实际 {r.status_code}")
r = client.post(f"/api/reports/{ops_id}/generate", headers=A)
check("GENERATE_DONE_409", r.status_code == 409, f"已完成报告再次生成应 409，实际 {r.status_code}")

# ---------- 市场分析周报：无研究源失败；有研究报告则成功 ----------
r = client.post("/api/reports", headers=A, json={"report_type": "市场分析周报", **empty_period})
market_empty_id = r.json().get("id")
r = client.post(f"/api/reports/{market_empty_id}/generate", headers=A)
check(
    "MARKET_EMPTY_FAIL",
    r.status_code == 400 and "拒绝伪造" in str(r.json().get("detail", "")),
    "市场周报空源失败",
)

from app.models.phase2 import ResearchReport, ResearchReportStatus, ResearchTask, ResearchTaskStatus  # noqa: E402

db = SessionLocal()
try:
    research_task = ResearchTask(
        task_no=f"RT{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        topic="企业获客趋势",
        objective="观察本周竞对与行业变化",
        scope_config={},
        status=ResearchTaskStatus.success,
        requested_by=1,
    )
    db.add(research_task)
    db.flush()
    db.add(ResearchReport(
        research_task_id=research_task.id,
        title="本周获客趋势研究",
        summary="短视频获客成本上升，需验证私域承接。",
        content="根据检索，获客成本上升。引用见来源。",
        sections={"趋势": "获客成本上升"},
        conclusions={"建议": "观察私域承接"},
        is_ai_product=True,
        status=ResearchReportStatus.success,
        source_count=1,
    ))
    db.commit()
finally:
    db.close()

r = client.post("/api/reports", headers=A, json={"report_type": "市场分析周报", **period})
market_id = r.json().get("id")
r = client.post(f"/api/reports/{market_id}/generate", headers=A)
market = r.json()
check(
    "MARKET_GENERATE_200",
    r.status_code == 200 and market.get("generation_status") == "已完成",
    f"市场周报生成 {r.status_code} status={market.get('generation_status')}",
)
market_types = {item.get("type") for item in ((market.get("source_snapshot") or {}).get("sources") or [])}
check("MARKET_SOURCES", "research_report" in market_types, f"市场周报来源={market_types}")

# ---------- 推送骨架 501 ----------
r = client.post(f"/api/reports/{ops_id}/push-tasks", headers=A, json={
    "channel": "飞书",
    "recipient_type": "指定人",
    "target_object": "ops-group-demo",
})
push_id = r.json().get("id")
check(
    "PUSH_CREATE",
    r.status_code == 200 and r.json().get("status") == "待推送" and push_id,
    "已完成报告可创建推送任务",
)
r = client.post(f"/api/reports/{empty_id}/push-tasks", headers=A, json={
    "channel": "微信",
    "target_object": "should-fail",
})
check("PUSH_ONLY_DONE", r.status_code == 400, "未完成报告不可创建推送")

r = client.post(f"/api/push-tasks/{push_id}/execute", headers=A)
check(
    "PUSH_501",
    r.status_code == 501 and "待实测" in str(r.json().get("detail", "")),
    f"推送执行 501，实际 {r.status_code} {r.json().get('detail')}",
)
r = client.get(f"/api/push-tasks/{push_id}", headers=A)
push = r.json()
check(
    "PUSH_RECORD_FAIL",
    push.get("status") == "失败"
    and (push.get("records") or [{}])[0].get("error_code") == "CHANNEL_API_NOT_IMPLEMENTED",
    "501 后任务失败并留下错误码，不伪装已推送",
)

# ---------- 列表筛选 ----------
r = client.get("/api/reports", headers=A, params={"report_type": "运营数据报告", "page_size": 50})
check("LIST_FILTER", r.status_code == 200 and r.json().get("total", 0) >= 1, "按类型筛选列表")

print("\n======== 汇总 ========")
failed = [item for item in RESULTS if item[1] == "未通过"]
for code, status, note in RESULTS:
    print(f"{status}\t{code}\t{note}")
print(f"通过 {len(RESULTS) - len(failed)}/{len(RESULTS)}")
sys.exit(1 if failed else 0)
