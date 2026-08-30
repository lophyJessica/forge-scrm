# 选题批量导出 CSV G2 — 开发指令

> 日期：2026-08-31
> 依据：audit-reviews/PRD与前端对齐复审-20260830.md（G2 为"未做"，PRD 定位 In Scope"希望有"，P1 尾巴）
> 范围：选题库模块，活小独立。前后端均可改。可与 33/34 并行（文件域不重叠）。

## 指令正文（复制给 Codex，独立会话）

```plaintext
cd forge-scrm 仓库根目录（Mac 本地实际路径），不新建任何目录。开工前先 git pull origin main。

Context:
二期缺口最后一项 G2：选题批量导出 CSV。PRD 定位 In Scope（希望有），选题库主PRD.md:28-33。现状：TopicList.tsx 只有筛选/详情/选中淘汰/新增生成入口，后端 topics 路由无导出接口。本轮前后端均可改，活小。⚠️表单字段 name 禁用 style/name/title/action 等 HTML 原生属性名。

Request:
1. 后端：新增导出接口 GET /topics/export（与既有列表同鉴权）——支持与列表页相同的筛选参数（关键词/方向/状态等），返回 CSV 文件（Content-Type: text/csv; charset=utf-8，加 BOM 保证 Excel 打开中文不乱码）。导出列按核心字段清单的选题字段：ID/标题/方向/状态/来源/生成批次/创建时间（以 context/05 字段口径为准，禁止自造字段）。加导出行数上限（如 5000 行）防止内存失控，超限报错提示缩小筛选范围。
2. 前端：TopicList.tsx 工具栏加「导出 CSV」按钮（secondary 层级，遵守按钮层级规范）——携带当前筛选条件请求导出接口并下载文件（文件名：选题导出_YYYYMMDD.csv）。导出前弹确认显示"将按当前筛选条件导出"。空结果时提示无数据不请求。
3. 状态列导出值用 displayStatus 映射后的用户可见状态（不含"待审核"等预留态字样，遵守审核字样口径——导出文件里也不得出现）。

红线禁止:
- 前端不得出现"审核/抽查"字样（含导出文件内容）
- 禁止新造 context 未定义字段；CSV 列以 context/05 字段口径为准
- 禁止 commit/push/部署
- 遵守 AGENTS.md 工作流铁律

Checkpoint:
完成后生成自检报告 check-reports/G2选题导出CSV-自检报告-20260831.md，含：改动文件、接口定义、CSV 列清单与字段口径对照、行数上限策略、build/tsc/compileall 证明、遗留风险。沙箱网络受限则报告留本地，由杰西卡代传管道。
```
