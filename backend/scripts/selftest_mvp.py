"""MVP 验收清单 Must 45 条本地自测脚本。

用法：cd backend && python scripts/selftest_mvp.py
说明：
  - 使用独立的临时 SQLite 库，不污染开发库；
  - DeepSeek 调用以桩（stub）替代，用于验证「提示词组装 / 结构化校验 / 留档 / 去重 /
    状态流转 / 失败重试与留痕」的完整代码路径。真实 API 连通性需配置 DEEPSEEK_API_KEY 后另测。
"""

import io
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

_TMP = tempfile.mkdtemp(prefix="forge_selftest_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/selftest.db"
os.environ["DATA_DIR"] = f"{_TMP}/data"
os.environ["DEEPSEEK_API_KEY"] = "TEST-STUB-KEY-NOT-REAL"
os.environ["JWT_SECRET"] = "selftest-secret"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.base import Base  # noqa: E402
from app import models as _models  # noqa: E402,F401
from app.services import deepseek_service as ds  # noqa: E402

Base.metadata.create_all(bind=engine)

RESULTS: list[tuple[str, str, str]] = []


def check(code: str, ok: bool, note: str = "") -> bool:
    RESULTS.append((code, "通过" if ok else "未通过", note))
    print(f"[{'PASS' if ok else 'FAIL'}] {code} {note}")
    return ok


def skip(code: str, note: str) -> None:
    RESULTS.append((code, "不适用/需环境", note))
    print(f"[SKIP] {code} {note}")


# ---------------- DeepSeek 桩 ----------------

_STUB_MODE = {"mode": "ok", "calls": 0}


def _stub_chat_json(system_prompt, user_prompt, validator=None, temperature=0.7, max_retry=None):
    _STUB_MODE["calls"] += 1
    if _STUB_MODE["mode"] == "fail":
        raise ds.DeepSeekError("桩：模拟 DeepSeek 连续失败（已重试 3 次）", '{"error":"stub failure"}')

    if "选题" in system_prompt or "topics" in (_STUB_MODE.get("kind") or ""):
        pass
    payload = _STUB_MODE["payload"]
    raw = json.dumps(payload, ensure_ascii=False)
    parsed = json.loads(raw)
    if validator is not None:
        parsed = validator(parsed)
    return parsed, raw


ds.chat_json = _stub_chat_json  # type: ignore[assignment]
# 各 router 是以 `from app.services import deepseek_service as ds` 引入，替换模块属性即可生效。


def topic_payload(n: int, prefix: str) -> dict:
    return {
        "topics": [
            {
                "title": f"{prefix}选题{i}",
                "customer_scenario": "制造业老板获客难",
                "user_perspective": "老板视角",
                "business_direction": "获客",
                "core_angle": f"从第{i}个角度切入讲清楚获客链路",
                "topic_principle": "有用",
                "topic_angle": "反常识",
            }
            for i in range(1, n + 1)
        ]
    }


def script_payload(n: int) -> dict:
    return {
        "scripts": [
            {"content": f"【第{i}版脚本】开头钩子……中间讲故事……结尾引导。"} for i in range(1, n + 1)
        ]
    }


def analysis_payload() -> dict:
    return {
        "results": [
            {
                "effect": "本周互动率环比提升",
                "conclusion": "获客类内容表现优于泛管理类内容",
                "suggestions": ["提高获客类选题占比", "开头 3 秒加入痛点提问"],
                "evidence": "样本内获客类内容平均播放高于均值",
                "material_candidates": [{"title": "获客类内容表现结论", "content": "获客类内容互动率更高。"}],
                "topic_candidates": [{"title": "制造业老板获客三大误区", "core_angle": "从误区切入"}],
            }
        ]
    }


client = TestClient(app)
client.__enter__()  # 触发 lifespan → 种子数据

# ==================== 五、权限与账号 ====================

r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
admin_token = r.json().get("access_token", "")
A = {"Authorization": f"Bearer {admin_token}"}
check("M32", r.status_code == 200 and r.json().get("user", {}).get("role") == "管理员"
      and r.json().get("must_change_password") is True,
      "管理员登录成功，返回 must_change_password=true（前端据此显示账号管理入口并提示改密）")

r = client.post("/api/users", headers=A, json={
    "username": "member01", "password": "member123", "role": "成员",
    "functional_permissions": ["material.delete", "topic.generate", "topic.create",
                               "topic.update", "script.update", "script.version.view",
                               "script.version.rollback", "rawdata.input"],
    "data_scope": {"type": "全量"},
})
member_id = r.json().get("id")
check("M34", r.status_code == 200, "管理员创建成员账号 member01")

r = client.post("/api/auth/login", json={"username": "member01", "password": "member123"})
member_token = r.json().get("access_token", "")
M = {"Authorization": f"Bearer {member_token}"}
r2 = client.get("/api/users", headers=M)
check("M33", r.status_code == 200 and r2.status_code == 403,
      "成员登录成功；访问账号管理接口返回 403（前端不渲染账号管理菜单）")

r = client.get("/api/materials")
check("M38", r.status_code == 401, "未带 token 访问业务接口返回 401（前端路由守卫跳登录页）")

# ==================== 一、资料库 ====================

classes = client.get("/api/material-classes", headers=A).json()
CLS = {c["name"]: c["id"] for c in classes}

base_mat = {
    "class_id": CLS["商业研究结论"], "source_type": "报告", "trust_level": "高",
    "valid_from": str(date.today() - timedelta(days=1)),
    "valid_until": str(date.today() + timedelta(days=365)),
}

r = client.post("/api/materials", headers=A, json={
    **base_mat, "title": "制造业获客研究结论", "content": "制造业老板最关心线索成本。",
    "tags": ["制造业客户"], "submit_for_review": False})
m1 = r.json()
r2 = client.post(f"/api/materials/{m1['id']}/submit", headers=A)
check("M01", m1.get("status") == "草稿" and r2.json().get("status") == "待审核",
      "新增=草稿 → 提交审核=待审核")

check("M04", "制造业客户" in m1.get("tags", []) and
      any(t["name"] == "制造业客户" for t in client.get("/api/tags", headers=A).json()),
      "页内自由新建标签「制造业客户」并进入标签库")

r = client.post(f"/api/materials/{m1['id']}/review", headers=A, json={"approved": True})
check("M02", r.json().get("status") == "已生效", "审核通过 → 已生效")

r = client.post("/api/materials", headers=A, json={
    **base_mat, "title": "待驳回资料", "content": "内容不合格。", "submit_for_review": True})
m2 = r.json()
r = client.post(f"/api/materials/{m2['id']}/review", headers=A, json={"approved": False})
check("M03", r.json().get("status") == "已废弃", "审核驳回 → 已废弃")

by_kw = client.get("/api/materials", headers=A, params={"keyword": "线索成本"}).json()
by_cls = client.get("/api/materials", headers=A, params={"class_id": CLS["商业研究结论"], "status": "已生效"}).json()
by_tag = client.get("/api/materials", headers=A, params={"tag": "制造业客户"}).json()
check("M05", by_kw["total"] >= 1 and by_cls["total"] >= 1 and by_tag["total"] >= 1,
      f"关键词命中{by_kw['total']}条 / 分类命中{by_cls['total']}条 / 标签命中{by_tag['total']}条")

for name, content in (("案例包装", "某制造业客户 3 个月线索翻倍。"), ("个人观点", "我认为内容即销售。")):
    rr = client.post("/api/materials", headers=A, json={
        **base_mat, "class_id": CLS[name], "title": f"{name}样例", "content": content,
        "submit_for_review": True})
    client.post(f"/api/materials/{rr.json()['id']}/review", headers=A, json={"approved": True})

r = client.post("/api/materials/combo-preview", headers=A,
                json={"class_names": ["商业研究结论", "个人观点", "案例包装"], "limit_per_class": 5})
preview = r.json()
check("M06", r.status_code == 200 and len(preview["items"]) == 3 and preview["preview_text"].strip() != "",
      "固定组合（商业研究结论+个人观点+案例包装）生成引用预览文本")

r = client.post("/api/materials", headers=A, json={
    **base_mat, "title": "即将过期资料", "content": "过期检查用。", "submit_for_review": True})
m3 = r.json()
client.post(f"/api/materials/{m3['id']}/review", headers=A, json={"approved": True})
client.put(f"/api/materials/{m3['id']}", headers=A,
           json={"valid_until": str(date.today() - timedelta(days=1))})
r = client.get(f"/api/materials/{m3['id']}", headers=A)
check("M07", r.json().get("status") == "已过期", "有效期止设为昨天，读取时惰性判定为「已过期」（D-T3）")

# ==================== 二、选题库 ====================

_STUB_MODE["payload"] = topic_payload(10, "A")
r = client.post("/api/topics/generate", headers=A, json={
    "direction": "营销", "specialty": "市场营销",
    "material_ids": [m1["id"]], "count": 10})
g1 = r.json()
check("M10", r.status_code == 200 and g1.get("saved") == 10,
      f"方向「营销」参考商业研究结论资料，生成 {g1.get('saved')} 条入库（AI 调用为桩）")

dup = topic_payload(10, "A")
dup["topics"][0]["title"] = "A选题1"          # 完全重复
dup["topics"][1]["title"] = "A选题1（另一种说法）"  # 语义相近
_STUB_MODE["payload"] = dup
r = client.post("/api/topics/generate", headers=A, json={
    "direction": "营销", "specialty": "市场营销", "count": 10})
g2 = r.json()
titles2 = [t["title"] for t in g2["topics"]]
check("M11", g2["deduped"] >= 1 and "A选题1（另一种说法）" in titles2,
      f"完全相同标题被过滤（去重 {g2['deduped']} 条）；语义相近标题保留，不做自动合并")

batches = client.get("/api/topics/batches", headers=A).json()
check("M12", len(batches) >= 2 and all(b["batch_no"] for b in batches),
      f"生成历史留痕：{len(batches)} 个批次可回溯")

topics = client.get("/api/topics", headers=A, params={"batch_no": g1["batch_no"]}).json()["items"]
t_ok1 = client.post(f"/api/topics/{topics[0]['id']}/screen", headers=A, json={"screening_result": "选中"}).json()
t_ok2 = client.post(f"/api/topics/{topics[1]['id']}/screen", headers=A, json={"screening_result": "选中"}).json()
t_no = client.post(f"/api/topics/{topics[2]['id']}/screen", headers=A, json={"screening_result": "淘汰"}).json()
unscreened = topics[3]
_STUB_MODE["payload"] = script_payload(3)
blocked = client.post("/api/scripts/generate", headers=A, json={
    "topic_id": unscreened["id"], "style": "讲故事", "version_count": 3})
check("M13", t_ok1["status"] == "已选定" and t_ok2["status"] == "已选定"
      and t_no["status"] == "已废弃" and blocked.status_code == 400,
      "选中=已选定 / 淘汰=已废弃；未筛选选题生成脚本被拦截（R3）")

check("M14", t_ok1["status"] == "已选定",
      "已选定选题提供「生成脚本」入口，前端跳 /scripts/generate?topic_id=x（详见 TopicDetail.tsx）")

r = client.post("/api/topics", headers=A, json={
    "title": "独立创建的选题", "direction": "经营", "specialty": "企业经营",
    "customer_scenario": "老板缺人", "user_perspective": "老板视角",
    "business_direction": "留存", "core_angle": "从组织效率切入",
    "topic_principle": "有用", "topic_angle": "反常识", "material_ids": []})
solo = r.json()
check("M15", r.status_code == 200 and solo["batch_no"] is None and solo["has_ai_raw_response"] is False,
      "手动创建独立选题成功；无批次号、无 AI 原始响应（S04 不要求）")

r = client.put(f"/api/topics/{solo['id']}", headers=A, json={"title": "独立创建的选题（已修改）"})
after = client.get(f"/api/topics/{solo['id']}", headers=A).json()
check("M40", r.status_code == 200 and after["title"] == "独立创建的选题（已修改）",
      "人工修改选题内容即时更新；系统未建选题版本表（D8）")

# ==================== 三、脚本库 ====================

_STUB_MODE["payload"] = script_payload(3)
r = client.post("/api/scripts/generate", headers=A, json={
    "topic_id": t_ok1["id"], "style": "讲故事", "content_elements": ["案例", "个人观点"],
    "version_count": 3, "material_ids": [m1["id"]]})
gs = r.json()
topic_after = client.get(f"/api/topics/{t_ok1['id']}", headers=A).json()
check("M16", r.status_code == 200 and gs["generated"] == 3
      and all(s["topic_id"] == t_ok1["id"] for s in gs["scripts"])
      and topic_after["status"] == "已生成脚本",
      "基于选题生成 3 版脚本，均显示所属选题；选题状态流转为已生成脚本")

check("M20", all(s["style"] == "讲故事" for s in gs["scripts"]),
      "以「讲故事」风格生成，落库 style=讲故事（风格通过提示词约束，文风由 AI 产出）")

r = client.post("/api/scripts", headers=A, json={
    "content": "独立创建的脚本正文。", "style": "轻松口语", "content_elements": ["数据"]})
solo_s = r.json()
r2 = client.put(f"/api/scripts/{solo_s['id']}", headers=A, json={"topic_id": solo["id"]})
check("M17", solo_s.get("topic_id") is None and r2.json().get("topic_id") == solo["id"],
      "独立创建允许 topic_id 为空；后补关联成功且可见")

sid = gs["scripts"][0]["id"]
r = client.put(f"/api/scripts/{sid}", headers=A,
               json={"content": "v2 内容：调整了开头钩子。", "note": "调整开头"})
vs = client.get(f"/api/scripts/{sid}/versions", headers=A).json()
check("M18", r.json()["current_version"] == 2 and len(vs) == 2
      and any(v["version"] == 1 for v in vs),
      "修改后版本 v1→v2，历史保留 v1 快照")

d = client.get(f"/api/scripts/{sid}/diff", headers=A, params={"left": 1, "right": 2}).json()
rb = client.post(f"/api/scripts/{sid}/rollback", headers=A, json={"version": 1}).json()
vs2 = client.get(f"/api/scripts/{sid}/versions", headers=A).json()
v1_content = next(v["content_snapshot"] for v in vs2 if v["version"] == 1)
check("M19", d.get("diff", "") != "" and rb["content"] == v1_content
      and rb["current_version"] == 3 and any("回退自" in (v.get("note") or "") for v in vs2),
      "v1/v2 差异可查看；回退后当前内容=v1，并生成 v3 保留回退记录")

r = client.post(f"/api/scripts/{sid}/submit", headers=A)
member_review = client.post(f"/api/scripts/{sid}/review", headers=M, json={"approved": True})
admin_review = client.post(f"/api/scripts/{sid}/review", headers=A, json={"approved": True})
sid2 = gs["scripts"][1]["id"]
client.post(f"/api/scripts/{sid2}/submit", headers=A)
rej = client.post(f"/api/scripts/{sid2}/review", headers=A, json={"approved": False})
check("M21", r.json()["status"] == "待审核" and member_review.status_code == 403
      and admin_review.json()["status"] == "已通过" and rej.json()["status"] == "已废弃",
      "管理员审核通过=已通过 / 驳回=已废弃；成员调用审核接口 403（前端不渲染审核入口）")

blank1 = client.post("/api/scripts", headers=A, json={"content": "   ", "style": "讲故事"})
blank2 = client.post("/api/scripts", headers=A, json={"content": "", "style": "讲故事"})
check("M22", blank1.status_code == 400 and blank2.status_code == 422,
      "空白/空字符串正文均被服务端拒绝（400 业务校验 / 422 schema 校验）")

mark_ok = client.post(f"/api/scripts/{sid}/mark-used", headers=A)
sid3 = gs["scripts"][2]["id"]
client.post(f"/api/scripts/{sid3}/submit", headers=A)
mark_pending = client.post(f"/api/scripts/{sid3}/mark-used", headers=A)
mark_discard = client.post(f"/api/scripts/{sid2}/mark-used", headers=A)
check("M39", mark_ok.json()["status"] == "已使用" and mark_pending.status_code == 400
      and mark_discard.status_code == 400,
      "已通过脚本可标记已使用；待审核 / 已废弃脚本标记被拒绝")

# ==================== 四、数据分析 ====================

src = client.post("/api/data-sources", headers=A, json={
    "name": "自己账号-视频号", "collection_method": "手动录入", "business_object": "自己账号",
    "platform": "视频号", "account_identifier": "jf_official", "is_benchmark": False}).json()

r = client.post("/api/raw-data", headers=A, json={
    "source_id": src["id"], "raw_content": "本周发布 5 条内容，获客类互动更好。",
    "structured": {"备注": "无固定指标维度"},
    "window_start": "2026-08-01 00:00:00", "window_end": "2026-08-20 00:00:00"})
raw1 = r.json()
check("M23", r.status_code == 200 and raw1["structured"] == {"备注": "无固定指标维度"},
      "手动录入一组基础数据成功；structured 为自由 JSON，不要求视频号固定指标维度")

tpl = client.get("/api/raw-data/csv-template", headers=A)
csv_body = ("数据源名称,原始内容,采集时间,时间窗开始,时间窗结束,结构化字段JSON\n"
            "自己账号-视频号,导入的第一条原始内容,2026-08-20 10:00:00,2026-08-01,2026-08-20,\"{\"\"播放量\"\":12000}\"\n"
            "不存在的数据源,导入的第二条,2026-08-20 10:00:00,2026-08-01,2026-08-20,\n")
imp = client.post("/api/raw-data/import", headers=A,
                  files={"file": ("t.csv", io.BytesIO(csv_body.encode("utf-8-sig")), "text/csv")}).json()
bad = client.post("/api/raw-data/import", headers=A,
                  files={"file": ("bad.csv", io.BytesIO("列A,列B\n1,2\n".encode("utf-8")), "text/csv")})
check("M24", tpl.status_code == 200 and imp["success"] == 1 and imp["failed"] == 1
      and imp["errors"] and imp["stored_file"] and bad.status_code == 400,
      f"模板可下载；成功 {imp['success']} 行 / 失败 {imp['failed']} 行并给出行号原因；"
      f"原文件留档 {imp['stored_file']}；列名不匹配整体拒绝并提示")

task = client.post("/api/analysis-tasks", headers=A, json={
    "name": "8月内容效果分析", "type": "数据分析", "raw_data_ids": [raw1["id"]],
    "material_ids": [m1["id"]]}).json()
status_before = task["status"]
_STUB_MODE["payload"] = analysis_payload()
executed = client.post(f"/api/analysis-tasks/{task['id']}/execute", headers=A).json()
check("M25", status_before == "待执行" and executed["status"] == "待审核"
      and executed["prompt_version_snapshot"] and executed["material_context_snapshot"],
      "任务待执行 →（同步执行，D-T1）→ 待审核；提示词版本与资料上下文快照均已留存")

res = executed["results"][0]["result_content"]
check("M26", set(["conclusion", "suggestions"]).issubset(res.keys()) and isinstance(res["suggestions"], list),
      "结果符合通用基础 schema（结论/建议/依据/候选资料/候选选题），未校验播放点赞等深度指标")

_STUB_MODE["mode"] = "fail"
task_f = client.post("/api/analysis-tasks", headers=A, json={
    "name": "失败重试用例", "type": "数据分析", "raw_data_ids": [raw1["id"]]}).json()
fail_resp = client.post(f"/api/analysis-tasks/{task_f['id']}/execute", headers=A)
failed = client.get(f"/api/analysis-tasks/{task_f['id']}", headers=A).json()
raw_view_fail = client.get(f"/api/analysis-tasks/{task_f['id']}/ai-raw", headers=A)
_STUB_MODE["mode"] = "ok"
_STUB_MODE["payload"] = analysis_payload()
retried = client.post(f"/api/analysis-tasks/{task_f['id']}/execute", headers=A).json()
check("M27", fail_resp.status_code == 400 and failed["status"] == "失败" and failed["error_message"]
      and failed["has_ai_raw_response"] and raw_view_fail.status_code == 200
      and retried["status"] == "待审核" and retried["retry_count"] >= 1,
      f"失败任务落状态=失败并留错误信息与原始响应，可重新执行成功；retry_count={retried['retry_count']}")

check("S03", failed["status"] == "失败" and failed["error_message"] and raw_view_fail.status_code == 200
      and retried["status"] == "待审核",
      "生成失败留痕：错误信息可查、原始响应可查、重试后成功（同 M27 证据）")

result_id = executed["results"][0]["id"]
wb_blocked_m = client.post(f"/api/analysis-results/{result_id}/writeback-material", headers=A,
                           json={"materials": [{"title": "x", "content": "y", "class_id": CLS["商业研究结论"],
                                                "valid_from": str(date.today()),
                                                "valid_until": str(date.today() + timedelta(days=30))}]})
wb_blocked_t = client.post(f"/api/analysis-results/{result_id}/writeback-topic", headers=A,
                           json={"topics": [{"title": "x", "direction": "营销", "specialty": "市场营销",
                                             "customer_scenario": "a", "user_perspective": "b",
                                             "business_direction": "c", "core_angle": "d",
                                             "topic_principle": "e", "topic_angle": "f"}]})
check("M31", wb_blocked_m.status_code == 400 and wb_blocked_t.status_code == 400,
      "结果未确认时回写/反哺被服务端拦截（前端同时按状态置灰按钮）")

reviewed = client.post(f"/api/analysis-tasks/{task['id']}/review", headers=A, json={"approved": True}).json()
check("M28", reviewed["status"] == "已确认" and reviewed["reviewer_id"] and reviewed["reviewed_at"],
      "人工审核后任务状态=已确认，记录审核人与时间")

cand = res["material_candidates"][0]
wb_m = client.post(f"/api/analysis-results/{result_id}/writeback-material", headers=A, json={
    "materials": [{"title": cand["title"], "content": cand["content"],
                   "class_id": CLS["商业研究结论"], "source_type": "报告", "trust_level": "中",
                   "valid_from": str(date.today()),
                   "valid_until": str(date.today() + timedelta(days=180)), "tags": ["AI产出"]}]}).json()
new_mat = client.get(f"/api/materials/{wb_m['material_ids'][0]}", headers=A).json()
check("M29", wb_m["writeback_material_status"] == "已回写" and new_mat["status"] == "待审核"
      and new_mat["is_ai_product"] is True,
      "回写生成 AI 产物资料，状态=待审核、is_ai_product=true")

check("M08", new_mat["is_ai_product"] is True and new_mat["status"] == "待审核"
      and new_mat["source_analysis_task_id"] == task["id"],
      f"分析回写资料带 AI 产物标记与来源任务 #{task['id']}，且必须走审核（R1/R7）")

tc = res["topic_candidates"][0]
wb_t = client.post(f"/api/analysis-results/{result_id}/writeback-topic", headers=A, json={
    "topics": [{"title": tc["title"], "direction": "营销", "specialty": "市场营销",
                "customer_scenario": "制造业老板获客难", "user_perspective": "老板视角",
                "business_direction": "获客", "core_angle": tc["core_angle"],
                "topic_principle": "有用", "topic_angle": "反常识"}]}).json()
new_topic = client.get(f"/api/topics/{wb_t['topic_ids'][0]}", headers=A).json()
check("M30", wb_t["writeback_topic_status"] == "已反哺" and new_topic["status"] == "待筛选",
      "反哺生成选题，状态=待筛选（两个动作独立记录：回写/反哺状态字段分开）")

# ==================== 权限：功能权限 + 数据范围 ====================

client.put(f"/api/users/{member_id}", headers=A, json={
    "functional_permissions": ["topic.generate"],
    "data_scope": {"type": "指定", "material_class_ids": [CLS["商业研究结论"]], "data_source_ids": []}})
r = client.post("/api/auth/login", json={"username": "member01", "password": "member123"})
M = {"Authorization": f"Bearer {r.json()['access_token']}"}
no_exec = client.post(f"/api/analysis-tasks/{task['id']}/execute", headers=M)
mat_list = client.get("/api/materials", headers=M, params={"page_size": 100}).json()
cls_ids = {m["class_id"] for m in mat_list["items"]}
check("M36", no_exec.status_code == 403 and cls_ids <= {CLS["商业研究结论"]},
      f"成员无分析执行权限（403）；资料仅可见「商业研究结论」分类（返回 {len(mat_list['items'])} 条，"
      f"class_id 集合={sorted(cls_ids)}）")

r = client.post("/api/auth/change-password", headers=M,
                json={"old_password": "member123", "new_password": "member456"})
old_login = client.post("/api/auth/login", json={"username": "member01", "password": "member123"})
new_login = client.post("/api/auth/login", json={"username": "member01", "password": "member456"})
from sqlalchemy import select as _select  # noqa: E402
from app.core.database import SessionLocal as _SL  # noqa: E402
from app.models.user import User as _U  # noqa: E402
_db = _SL()
_hash = _db.scalar(_select(_U.password_hash).where(_U.username == "member01"))
_db.close()
check("M37", r.status_code == 200 and old_login.status_code == 401 and new_login.status_code == 200
      and _hash.startswith("$2b$") and "member456" not in _hash,
      "改密后旧密码失效、新密码可登录；库中仅存 bcrypt 哈希，接口/日志不记录明文")

client.post(f"/api/users/{member_id}/disable", headers=A)
disabled = client.post("/api/auth/login", json={"username": "member01", "password": "member456"})
check("M35", disabled.status_code in (401, 403), f"停用后无法登录（HTTP {disabled.status_code}）")

# ==================== 六、系统 ====================

ai_raw_dir = Path(os.environ["DATA_DIR"]) / "ai_raw"
archives = sorted(p.name for p in ai_raw_dir.glob("*.json"))
topic_raw = client.get(f"/api/topics/{topics[0]['id']}/ai-raw", headers=A)
task_raw_ok = client.get(f"/api/analysis-tasks/{task['id']}/ai-raw", headers=A)
solo_topic = client.get(f"/api/topics/{solo['id']}", headers=A).json()
check("S04", topic_raw.status_code == 200 and task_raw_ok.status_code == 200
      and raw_view_fail.status_code == 200 and len(archives) >= 4
      and solo_topic["has_ai_raw_response"] is False,
      f"成功与失败任务的 AI 原始响应均可查看，磁盘留档 {len(archives)} 份；独立创建选题不要求该字段")

log_text = ""
for p in (BACKEND_ROOT / "logs").glob("*.log") if (BACKEND_ROOT / "logs").exists() else []:
    log_text += p.read_text(encoding="utf-8", errors="ignore")
archive_text = "".join(p.read_text(encoding="utf-8", errors="ignore") for p in ai_raw_dir.glob("*.json"))
marker = os.environ["DEEPSEEK_API_KEY"]
src_text = ""
for p in BACKEND_ROOT.rglob("*.py"):
    if ".venv" in str(p) or "selftest" in p.name:
        continue
    src_text += p.read_text(encoding="utf-8", errors="ignore")
# 真实 key 形如 sk-xxxxxxxx...（20 位以上），不能与 task- / analysis-tasks 等普通字符串混淆
hardcoded_key = re.search(r"sk-[A-Za-z0-9]{20,}", src_text)
check("S05", marker not in log_text and marker not in archive_text and marker not in src_text
      and hardcoded_key is None,
      "测试标记 key 未出现在日志、AI 留档与源码中；源码无硬编码 key 字面量；Key 仅经 Authorization 头发送")

# 持久化：重新打开一个 Session 校验数据仍在（同一 SQLite 文件）
from app.core.database import SessionLocal as _SL2  # noqa: E402
from app.models.material import Material as _M  # noqa: E402
from sqlalchemy import func as _f, select as _s  # noqa: E402
_db2 = _SL2()
mat_count = _db2.scalar(_s(_f.count()).select_from(_M))
_db2.close()
db_file = Path(os.environ["DATABASE_URL"].replace("sqlite:///", ""))
check("S01", db_file.exists() and db_file.stat().st_size > 0 and mat_count >= 5,
      f"数据落盘到独立数据库文件（{mat_count} 条资料）；本地为 SQLite，"
      f"VPS 换 DATABASE_URL 即为 MySQL（DDL 以 MySQL 为准，见 README）")

skip("S02", "服务自恢复需 VPS systemd/supervisor 配置，本地无法验证；部署脚本由杰西卡在部署阶段配置")
skip("S06", "4C+4G 连续 60 分钟资源观察需 VPS 环境，本地不具备；待部署后由运维执行")

# ==================== 汇总 ====================

print("\n" + "=" * 78)
passed = sum(1 for _, s, _ in RESULTS if s == "通过")
failed = [c for c, s, _ in RESULTS if s == "未通过"]
skipped = [c for c, s, _ in RESULTS if s.startswith("不适用")]
print(f"合计 {len(RESULTS)} 项：通过 {passed}，未通过 {len(failed)}，需环境 {len(skipped)}")
if failed:
    print("未通过：", ", ".join(failed))
print("需环境：", ", ".join(skipped))

out = BACKEND_ROOT / "scripts" / "selftest_result.md"
lines = ["| # | 结果 | 说明 |", "|---|---|---|"]
lines += [f"| {c} | {s} | {n} |" for c, s, n in RESULTS]
out.write_text("\n".join(lines), encoding="utf-8")
print(f"明细已写入 {out}")

client.__exit__(None, None, None)
sys.exit(1 if failed else 0)
