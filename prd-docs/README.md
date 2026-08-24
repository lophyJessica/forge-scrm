# PRD 文档目录

本目录存放完成业务确认、可作为开发依据的正式 PRD。

## 当前文档

| 文档 | 状态 |
|---|---|
| 主PRD.md | ✅ 定稿（7+1 项待确认已全部回收回写） |
| 核心字段清单.md | ✅ 完成（13+ 实体，MySQL 建表依据） |
| mvp验收清单.md | ✅ 完成（41 用例，可勾选） |
| modules/01-资料库PRD.md | ✅ 初稿 |
| modules/02-选题库PRD.md | ✅ 初稿 |
| modules/03-脚本库PRD.md | ✅ 初稿 |
| modules/04-数据分析PRD.md | ✅ 初稿 |
| modules/05-权限与账号PRD.md | ✅ 初稿 |

## 规则

- 正式 PRD 基于 context/ 生成，不重复定义字段/状态/枚举；
- 字段 SSOT 在 context/05，字段清单是展开版（建表依据）；
- 模块 PRD 按 templates/prd-template.md 结构；
- 待确认项确认后回写 context 再更新本目录文档；
- 一期 MVP 范围以 context/01 和主PRD §2 为准。