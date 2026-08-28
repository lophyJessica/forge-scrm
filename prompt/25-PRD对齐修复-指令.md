cd ~/个人文件/forge-scrm && git pull origin main

```plaintext
Context:
项目 forge-scrm（Forge 新媒体运营系统），Mac ~/个人文件/forge-scrm，main 分支。本任务是 PRD 对齐审计（audit-reviews/PRD与前端对齐审计-20260828.md，先读）后的修复轮 v2。
重要口径（0826 用户拍板 + 0828 重申）：二期审核默认通过——审核入口暂时隐藏不使用，逐条审核影响操盘手自用效率。覆盖 R3（选题人工筛选）/R6（分析结果审核）/R8（AI 产物审核）；R1（资料审核）在人工新建路径已由"新建资料免审核"（12 号指令，commit c9a11ae）实现直接生效；导入与 AI 产物路径的审核能力代码保留但不启用，后续可重新开启。拍板依据：prd-docs/modules/审核流程变更说明.md + requirements/09-二期调研结论.md。context/04 尚未回写该变更，本任务负责回写。
审计判定修正：audit 报告的 D1/D2/D3 三条不再作为代码缺陷修复——D1（资料双动作/有效期）被二期默认通过口径覆盖，人工创建已直接生效，有效期字段后端已有（schema valid_from/valid_until 默认值），前端无需恢复草稿/提交审核双动作；D2（成员审核放开）方向错误撤回；D3（选题锁定 10 条）保留执行。

Request:
【R-D3】选题每方向生成数量锁定（TopicGenerate.tsx）：
- 生成数量固定为 10（context/04 R4），移除 1-10 可编辑；UI 显示"每方向 10 条"。后端不改（前端固定传 10，保留后端弹性）。
【R-G3】生成页可选择已保存模板（TopicGenerate.tsx + ScriptGenerate.tsx）：
- 模板下拉改为请求 /api/prompt-templates?task_type=<对应>&status=启用，展示全部启用模板（内置+用户自建）；选中 → 提交带 prompt_template_id；自定义提示词模式优先级保持；不选 → 默认模板。两页一致。
【R-D4】模板管理补分析类（admin/PromptTemplates.tsx）：
- task_type 下拉补齐"资料分析、数据分析"；分析类 output_schema 必填（JSON 文本框 + 格式校验）。
【R-G1】固定组合引用预览（MaterialComboField.tsx）：
- 已勾选资料下方加"引用预览"折叠区（默认收起）：按组合顺序列出【分类】标题 + 内容前 200 字（复用已加载数据，零新接口）。
【R-Badge】ReportDetail.tsx 确认 Modal zIndex={1100} 存在（d3f6464 已改），存在则跳过。
【R-DOC 文档回写——本任务核心，仅允许改以下文件】
1. context/04-业务规则与状态机.md（⚠️ 唯一一次授权改 context，用户 0828 明确要求回写审核口径）：
   - R1 改为：资料使用规则——人工新建直接生效（二期默认）；导入资料与 AI 产物保留审核队列（待审核后可用）；审核入口暂时隐藏，保留能力可重新启用（0826 拍板，依据 requirements/09 + 审核流程变更说明）。
   - R3 改为：选题生成后默认可用，人工筛选变为主动抽查/审核重启时使用（入口保留）。
   - R6 改为：分析结果默认按已确认处理，审核变为抽查/重启时使用（入口保留）。
   - R8 补充：AI 产物默认可用但保持 AI 产物标记；AI 产物标识与原始事实区分不变。
   - 状态机图（资料/选题/分析）同步标注"二期默认通过"路径；每处注明"0826 拍板，依据审核流程变更说明.md"。
2. prd-docs/modules/数据报告/数据报告主PRD.md:321-331：删除报告/推送记录口径回写——报告删除：仅限无推送记录且非生成中的报告（有推送记录=对账凭证不可删）；推送任务删除：已推送=凭证不可删，仅待推送/失败/已取消可删（0828 拍板，已上线）。
3. prd-docs/modules/数据报告/推送任务取消删除与卡片跳转PRD.md:21-39：删除规则同步改为上述"已推送=凭证不可删"口径（当前正文与此不一致）。
4. prd-docs/modules/数据分析/数据分析主PRD.md、数据分析字段清单.md：数据源/原始数据/分析任务三处补"删除与归档策略：待确认（当前实现为管理员直接删除，保留/关联保护规则待定稿）"。
5. prd-docs/modules/审核流程变更说明.md：顶部加状态说明"⚠️ 本文件口径已于 2026-08-28 回写至 context/04，context 现为 SSOT"。
【R-UI】frontend/UI-DESIGN.md 第 7 节列表页骨架补一行：列表默认排序=创建/生成时间倒序（回退修改时间倒序），后端 order_by 落实（此为 draft/待办-全局列表默认排序规则.md 的规范落点；本轮只写规范，不改后端排序代码）。

Output format:
- 按编号逐项修。python -m compileall -q backend/app 通过 + npm run build 通过。
- 自检报告 check-reports/PRD对齐修复v2-自检报告-20260828.md：逐项改动+文件+自检+遗留（含二期 P0 缺口 G4-G11、G12-G15 未实现为已排期待办）。

红线禁止:
- 禁止不执行 git pull 就改文件。
- context/ 仅允许改 context/04 的 R1/R3/R6/R8 与对应状态机标注，其余文件与段落禁改。
- prd-docs/ 仅允许改任务 R-DOC 列出的 4 个文件的目标段落，其余禁改。
- 禁止把"审核入口隐藏"当作缺陷去"修复"（D1/D2 的原审计判定作废，按本指令口径执行）。
- 禁止 commit/push/deploy；禁止把 draft/ 待办混入本轮；禁止伪造构建结果。

Checkpoint:
完成后必须执行 AI 自检报告管道上传（沙箱 DNS 不解析 pmlophy.com 时按兜底规则：保存 check-reports/ + 如实汇报"未上传管道"，禁止重试超过1次）：
curl --noproxy '*' -X POST "https://pmlophy.com/p/jarvis/file/upload" -H "X-Jarvis-User: ai-reports" -F "file=@check-reports/PRD对齐修复v2-自检报告-20260828.md"
最后汇报：逐项完成状态、context/04 回写的规则原文、改动文件列表、build/compileall 结果、报告文件名与字节数、是否已上传管道。
```
