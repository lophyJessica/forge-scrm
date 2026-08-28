# 二期收尾：模板seed自动补 + 飞书推送 — 迭代PRD（v2 企业应用方案）

> 状态：已确认，待开发（v2：推送从 webhook 方案改为企业自建应用方案）
> 日期：2026-08-28
> 决策背景：定时生成（APScheduler）暂缓——会每天产生 LLM token 消耗，当前用户尚未消化系统使用，等二阶段调研后再启动。

## 任务一：模板 seed 启动自动补（治本）

### 背景

内置提示词模板（内置选题生成/内置脚本生成等，PromptTaskType 各类型的默认模板）当前仅靠一次性 seed 灌入；新库部署或数据重建后需手动补，易漏。

### 需求

后端启动 seed 流程（backend/app/services/seed.py 的 run_seed）新增 seed_builtin_templates：

- 对 PromptTaskType 每个类型检查是否存在该 task_type 的内置模板（判定：名称以"内置"开头且 task_type 匹配，与各 service 的 DEFAULT_SYSTEM_PROMPT 常量对应——以代码现状为准，最小改动）
- 缺失则创建：name="内置XX提示词"、content=对应 DEFAULT_SYSTEM_PROMPT、status=启用、version=1、created_by=种子管理员
- 幂等：已存在不重复创建、不覆盖用户修改
- 启动日志记录补了哪些

### 验收

1. 全新空库启动 → 自动出现全部 task_type 的内置模板
2. 已有库重启 → 不重复、不改动用户已改过的模板
3. 现网重启 → 行为与现状一致（已有模板不受影响）

## 任务二：数据报告飞书推送打通（企业自建应用方案）

### 背景

数据报告模块推送骨架已就绪（ReportPushTask/ReportPushRecord 表、创建/执行接口、状态机：待推送→推送中→已推送/失败+retry_count），执行接口的发送段为 501 TODO。本期只接飞书，微信暂缓。

### 方案：企业自建应用 + im/v1/messages

- 凭据经环境变量注入（禁止写死在代码/配置文件里）：
  - FEISHU_APP_ID（必需）
  - FEISHU_APP_SECRET（必需）
  - FEISHU_PUSH_USER_ID（必需，接收人 user_id，支持逗号分隔多个）
- 发送流程（backend/app/services/feishu_push.py）：
  1. 取 tenant_access_token：POST /open-apis/auth/v3/tenant_access_token/internal（app_id+app_secret），token 缓存至过期前 5 分钟刷新
  2. 发消息：POST /open-apis/im/v1/messages?receive_id_type=user_id，Authorization: Bearer <token>，body 为 interactive 卡片（report 用户的 user_id 已实测可换取 token，im:message 权限已开通）
  3. 卡片内容：报告标题、生成时间、核心数据摘要（以报告实体现有字段为准，超长截断 800 字）
- 失败处理：非 200 或飞书返回非 0 code → 推送记录标记失败+错误摘要，任务置失败（复用现有 retry_count 手动重试逻辑）；token 失效（code 99991663/99991661）自动刷新重试一次
- 记录留痕：ReportPushRecord 存响应摘要（不含 Authorization 头、不含 secret）

### 验收

1. 配好三个环境变量后，对已完成报告创建推送任务 → 执行 → 用户飞书收到卡片消息
2. 凭据错误/权限缺失 → 推送失败，记录里能看到飞书返回的 code+msg，可重试
3. 未配置环境变量 → 执行时报 BizError 提示"未配置飞书推送"，不是 501
4. secret/token 不出现在日志与数据库记录

### 凭据状态（用户提供，已实测）

- App ID 与接收人 user_id 已确认可用（tenant_access_token 获取实测 code=0）；im:message 权限已开通
- App Secret 由用户部署时自行配置到搬瓦工环境变量，不经聊天/代码传递

## 边界（不做）

- 定时生成/APScheduler：暂缓（token 消耗，等二阶段）
- 微信推送：后续渠道定稿再做
- open_id/通讯录映射：不需要（直接用 user_id 作 receive_id_type，已验证可行路径）
