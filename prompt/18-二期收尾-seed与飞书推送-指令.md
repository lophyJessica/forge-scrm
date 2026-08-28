cd ~/个人文件/forge-scrm && git pull origin main

```plaintext
Context:
项目 forge-scrm（Forge 新媒体运营系统），仓库位于 Mac ~/个人文件/forge-scrm，工作分支 main。本任务实现二期收尾两件事，PRD 见 prd-docs/modules/二期收尾-seed自动补与飞书推送PRD.md（先读，v2 企业应用方案）。
现状：
- seed 流程在 backend/app/services/seed.py（run_seed 启动时调用，已有 seed_admin/seed_material_classes 幂等先例）；内置模板常量在各 service（topic_service.DEFAULT_SYSTEM_PROMPT / script_service.DEFAULT_SYSTEM_PROMPT 等），prompt_template 表有 task_type/name/content/status/version 字段。
- 推送骨架在 backend/app/routers/reports.py：ReportPushTask/ReportPushRecord 表已有，执行接口 execute_push_task 的发送段是 501 TODO（搜索"在此接入飞书"），状态机待推送→推送中→已推送/失败+retry_count 已实现。
- 飞书侧已就绪：企业自建应用已建（App ID 用户持有），im:message 权限已开通，接收人 user_id 已确认。发消息用 receive_id_type=user_id（无需 open_id，无需通讯录权限）。
- 本期只接飞书企业应用推送；微信推送、定时生成(APScheduler)、open_id 映射明确不做。

Request:
1. 任务一 seed_builtin_templates（backend/app/services/seed.py）：
   - run_seed 新增调用 seed_builtin_templates(db)。
   - 对 PromptTaskType 每个枚举值检查：是否存在该 task_type 的内置模板（判定：name 以"内置"开头且 task_type 匹配）。缺失则创建：name="内置XX提示词"（XX=task_type 枚举中文值）、content=对应 service 的 DEFAULT_SYSTEM_PROMPT 常量、status=启用、version=1、created_by=种子管理员 id。
   - 幂等：存在即跳过，不覆盖、不更新用户改过的模板。
   - 日志记录本次补建的模板名。
2. 任务二 飞书推送（backend/app/routers/reports.py + 新建 backend/app/services/feishu_push.py）：
   - feishu_push.py 核心：
     a) get_tenant_token()：POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal（app_id+app_secret from settings），进程内缓存 token 至过期前 5 分钟（响应有 expire 字段，秒）。
     b) send_report_card(open_id, title, generated_at, digest)：POST https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id，body={"receive_id": open_id, "msg_type": "interactive", "content": "<卡片JSON字符串>"}；卡片含报告标题/生成时间/摘要（digest 截断 800 字）；HTTP 超时 10s。返回 (ok: bool, resp_summary: str)。【此链路已用真实凭据实测通：token 获取 code=0、卡片发送 code=0】
     c) 飞书 code 99991663/99991661（token 失效）→ 强制刷新 token 重试一次。
   - config.py 新增字段：feishu_app_id/feishu_app_secret/feishu_push_open_ids（均默认空字符串，从环境变量 FEISHU_APP_ID/FEISHU_APP_SECRET/FEISHU_PUSH_OPEN_IDS 读取；open_ids 支持逗号分隔多个接收人）。
   - execute_push_task 替换 501 段：任一必需配置缺失 → BizError("未配置飞书推送，请联系管理员设置 FEISHU_APP_ID/FEISHU_APP_SECRET/FEISHU_PUSH_OPEN_IDS")，任务状态回滚为待推送不留脏状态；逐个接收人发送，全部成功 → 任务置已推送；任一失败 → 任务置失败，记录存"接收人+失败原因摘要"；retry_count 逻辑保持现有行为（手动重试）。
   - 安全红线：secret/token 绝不写入数据库记录、日志、异常信息；ReportPushRecord 只存"接收人(open_id)+成功/失败+飞书code与msg摘要"。
3. 禁止扩界：不做定时任务/APScheduler、不做微信推送、不做前端改动（推送交互已有）、不动 context/ 与 prd-docs/、不改数据库模型结构（无需新表新列）、不做 user_id/通讯录查询功能（open_id 由运维侧用调试台换取后配进环境变量）。

Output format:
- 最小改动。后端完成后跑 python compileall 验证。
- 生成自检报告 check-reports/二期收尾-seed与飞书推送-自检报告-20260828.md（任务/改动文件/每文件改动点/自检结果/遗留风险）。

红线禁止:
- 禁止不执行 git pull 就改文件。
- 禁止修改 context/、prd-docs/、requirements/。
- 禁止 commit/push/deploy（交付代码与报告即可）。
- 禁止把 App Secret/tenant_access_token 写进代码、配置文件、日志或数据库记录（一律走环境变量）。
- 禁止伪造验证结果：compileall 失败必须修复后再交付。

Checkpoint:
完成后必须执行 AI 自检报告管道上传（沙箱 DNS 不解析 pmlophy.com 时按兜底规则：保存 check-reports/ + 如实汇报"未上传管道"，禁止重试超过1次）：
curl --noproxy '*' -X POST "https://pmlophy.com/p/jarvis/file/upload" -H "X-Jarvis-User: ai-reports" -F "file=@check-reports/二期收尾-seed与飞书推送-自检报告-20260828.md"
最后汇报：改动文件列表、compileall 结果、报告文件名与字节数、是否已上传管道。
```

部署验收阶段需要用户操作：
- 搬瓦工环境变量配置：FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_PUSH_USER_IDS（值由用户自行填写，Secret 不经聊天传递）
- 重启后端服务后亲测：数据报告 → 创建推送任务 → 执行 → 飞书收到卡片
