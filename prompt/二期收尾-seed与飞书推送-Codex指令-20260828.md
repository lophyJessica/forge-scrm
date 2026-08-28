cd ~/个人文件/forge-scrm && git pull origin main

```plaintext
Context:
项目 forge-scrm（Forge 新媒体运营系统），仓库位于 Mac ~/个人文件/forge-scrm，工作分支 main。本任务实现二期收尾两件事，PRD 见 prd-docs/modules/二期收尾-seed自动补与飞书推送PRD.md（先读）。
现状：
- seed 流程在 backend/app/services/seed.py（run_seed 启动时调用，已有 seed_admin/seed_material_classes 幂等先例）；内置模板常量在各 service（topic_service.DEFAULT_SYSTEM_PROMPT / script_service.DEFAULT_SYSTEM_PROMPT 等），prompt_template 表有 task_type/name/content/status/version 字段。
- 推送骨架在 backend/app/routers/reports.py：ReportPushTask/ReportPushRecord 表已有，执行接口 execute_push_task 的发送段是 501 TODO（约232行"在此接入飞书/微信发送"），状态机待推送→推送中→已推送/失败+retry_count 已实现。
- 本期只接飞书自定义机器人 webhook；微信推送、定时生成(APScheduler)明确不做。

Request:
1. 任务一 seed_builtin_templates（backend/app/services/seed.py）：
   - run_seed 新增调用 seed_builtin_templates(db)。
   - 对 PromptTaskType 每个枚举值检查：是否存在该 task_type 的内置模板（以"名称以'内置'开头且 task_type 匹配"为判定，与现有 DEFAULT 常量对应）。缺失则创建：name="内置XX提示词"、content=对应 service 的 DEFAULT_SYSTEM_PROMPT 常量、status=启用、version=1、created_by=种子管理员 id。
   - 幂等：存在即跳过，不覆盖、不更新用户改过的模板。
   - 日志记录本次补建的模板名。
2. 任务二 飞书推送（backend/app/routers/reports.py + 新建 backend/app/services/feishu_push.py）：
   - 新服务 feishu_push.py：send_feishu_webhook(title, digest) → 读环境变量 FEISHU_PUSH_WEBHOOK_URL（必需）、FEISHU_PUSH_SECRET（可选，配置则走加签 timestamp+sign，HMAC-SHA256 base64，按飞书官方自定义机器人签名算法）；POST JSON；消息用飞书 interactive 卡片（标题+生成时间+摘要，digest 超长截断 800 字）；返回 (ok: bool, resp_summary: str)。超时 10s。
   - execute_push_task 替换 501 段：未配置环境变量 → BizError("未配置飞书推送，请联系管理员设置 FEISHU_PUSH_WEBHOOK_URL")，任务状态回滚为待推送，不留脏状态；发送成功 → 任务置已推送、记录存响应摘要；失败 → 任务置失败+错误摘要，retry_count 逻辑保持现有行为（手动重试）。
   - 禁止把 webhook URL/secret 写进数据库记录、日志或代码；记录里只存"已发送/失败+原因摘要"。
   - config.py 加对应环境变量字段（默认空字符串）。
3. 禁止扩界：不做定时任务/APScheduler、不做微信推送、不做前端改动（推送交互已有）、不动 context/ 与 prd-docs/、不改数据库模型结构（无需新表新列）。

Output format:
- 最小改动。后端完成后跑 python compileall 验证。
- 生成自检报告 check-reports/二期收尾-seed与飞书推送-自检报告-20260828.md（任务/改动文件/每文件改动点/自检结果/遗留风险）。

红线禁止:
- 禁止不执行 git pull 就改文件。
- 禁止修改 context/、prd-docs/、requirements/。
- 禁止 commit/push/deploy（交付代码与报告即可）。
- 禁止把 webhook URL/secret/token 写进代码、配置文件、日志或数据库记录。
- 禁止伪造验证结果：compileall 失败必须修复后再交付。

Checkpoint:
完成后必须执行 AI 自检报告管道上传（沙箱 DNS 不解析 pmlophy.com 时按兜底规则：保存 check-reports/ + 如实汇报"未上传管道"，禁止重试超过1次）：
curl --noproxy '*' -X POST "https://pmlophy.com/p/jarvis/file/upload" -H "X-Jarvis-User: ai-reports" -F "file=@check-reports/二期收尾-seed与飞书推送-自检报告-20260828.md"
最后汇报：改动文件列表、compileall 结果、报告文件名与字节数、是否已上传管道。
```

部署前需用户提供（飞书推送验收用）：
- 测试飞书群的机器人 webhook URL（群设置→群机器人→自定义机器人添加）
- 是否启用加签（secret）
