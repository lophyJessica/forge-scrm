# 二期收尾：模板seed自动补 + 飞书推送 — 迭代PRD

> 状态：已确认，待开发
> 日期：2026-08-28
> 决策背景：定时生成（APScheduler）暂缓——会每天产生 LLM token 消耗，当前用户尚未消化系统使用，等二阶段调研后再启动。

## 任务一：模板 seed 启动自动补（治本）

### 背景

内置提示词模板（内置选题生成/内置脚本生成等，PromptTaskType 各类型的默认模板）当前仅靠一次性 seed 灌入；新库部署或数据重建后需手动补，易漏。

### 需求

后端启动 seed 流程（backend/app/services/seed.py 的 run_seed）新增 seed_builtin_templates：

- 对 PromptTaskType 每个类型检查是否存在该 task_type 的内置模板（判定：现有各 service 的 DEFAULT_SYSTEM_PROMPT 对应内容，或名称含"内置"且 task_type 匹配——以代码现状为准，最小改动）
- 缺失则创建：name="内置XX提示词"、content=对应 DEFAULT_SYSTEM_PROMPT、status=启用、version=1、created_by=种子管理员
- 幂等：已存在不重复创建、不覆盖用户修改
- 启动日志记录补了哪些

### 验收

1. 全新空库启动 → 自动出现全部 task_type 的内置模板
2. 已有库重启 → 不重复、不改动用户已改过的模板
3. 现网重启 → 行为与现状一致（已有模板不受影响）

## 任务二：数据报告飞书推送打通

### 背景

数据报告模块推送骨架已就绪（ReportPushTask/ReportPushRecord 表、创建/执行接口、状态机：待推送→推送中→已推送/失败+retry_count），执行接口的发送段为 501 TODO。本期只接飞书，微信暂缓。

### 方案：飞书自定义机器人 Webhook（最简，无需应用审核）

- 使用飞书群自定义机器人 webhook（出参 JSON POST），签名校验可选支持（secret 配置则启用加签）
- 凭据经环境变量注入：FEISHU_PUSH_WEBHOOK_URL、FEISHU_PUSH_SECRET（可选）——禁止写死在代码/配置文件里
- 消息格式：interactive 卡片或 text，含报告标题、生成时间、核心数据摘要（以报告实体现有字段为准，超长截断）
- 失败处理：非 200 或飞书返回非 0 code → 推送记录标记失败+错误信息，任务状态置失败（现有 retry_count 逻辑复用，手动重试）
- 记录留痕：每条推送记录存响应摘要（不含敏感头），复用现有 ReportPushRecord

### 验收

1. 配置 webhook 后，对已完成报告创建推送任务 → 执行 → 飞书群收到卡片消息
2. webhook 无效 → 推送失败，记录里能看到错误原因，可重试
3. 未配置 webhook 环境变量 → 执行时报 BizError 提示"未配置飞书推送"，不是 501
4. token/key 不出现在日志与数据库记录

### 需要用户提供（开发前确认）

- 一个测试飞书群的机器人 webhook URL（群设置→群机器人→自定义机器人）
- 是否启用加签（secret）

## 边界（不做）

- 定时生成/APScheduler：暂缓（token 消耗，等二阶段）
- 微信推送：后续渠道定稿再做
- 自动采集定时触发：随定时生成一起暂缓
