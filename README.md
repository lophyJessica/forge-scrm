# Forge SCRM

Forge 新媒体运营系统（SCRM：Social/Content Relationship Management）的需求、产品文档与后续系统实现仓库。

## 当前阶段

当前处于：

```text
需求地基 → 自动化平台调研 → 业务问题确认 → 系统规格 → 开发
```

已完成：

- Make + DeepSeek + 飞书 MVP 选题/脚本链路调研记录；
- 自动化平台候选调研；
- 三大业务板块初步定义。

尚未开始：

- 前端开发；
- 后端开发；
- MySQL 建库；
- 自动化平台安装；
- 生产部署。

## 目录结构

```text
forge-scrm/
├── context/          业务事实、术语、范围和长期规则（最高权威）
├── requirements/     需求调研、平台调研和阶段性选型
├── prd-docs/         经确认后的正式 PRD 产物
├── draft/            未确认的草稿、临时方案和讨论材料
├── docs/             架构图、流程图、技术说明和项目手册
├── templates/        PRD、字段清单、规则和 Agent 指令模板
├── prompt/           给 Codex、Workbuddy、Cursor 等 Agent 的执行指令
├── check-reports/    自检、审计和交付报告
└── README.md
```

## 文档权威层级

```text
context/ > templates/ > prd-docs/ > draft/
```

- `context/`：业务事实和已确认规则的唯一来源；
- `templates/`：文档结构模板，不承载业务事实；
- `prd-docs/`：正式需求产物；
- `draft/`：尚未确认的讨论材料，不能当作正式需求依据。

## 三大业务板块

1. 资料库：手动添加、自动采集、CSV/TXT 导入、资料分析和资料引用；
2. 选题库和脚本库：提示词调用资料库，生成、修改、审核和管理选题/脚本；
3. 数据分析：自动采集、手动填写、CSV/TXT 导入、提示词分析和结构化结果。

## 现有 MVP

```text
网页表单 → Make Webhook → DeepSeek → 飞书 API → 选题库/脚本库
```

MVP 是已验证的过渡能力，不是最终系统架构。长期目标是自建运营系统、后端 API、MySQL 和对象存储；自动化平台通过 API 作为可替换执行层，不能直接绕过后端写 MySQL。

## 当前需求文件

请从 `requirements/` 中按编号阅读。任何内容进入 `prd-docs/` 前，必须先完成业务确认，并回写 `context/` 中的事实和规则。
