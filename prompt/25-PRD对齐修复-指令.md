cd ~/个人文件/forge-scrm && git pull origin main

```plaintext
Context:
项目 forge-scrm（Forge 新媒体运营系统），Mac ~/个人文件/forge-scrm，main 分支。本任务是 PRD 对齐审计后的修复轮：只做 MVP 阻塞修复 5 项 + 文档回写。审计报告全文见 audit-reviews/PRD与前端对齐审计-20260828.md（先读，各条 ID/PRD 依据/代码位置以报告为准）。
修复原则：以 context/ 和 MVP 验收清单为 SSOT；本次【不改】prd-docs/（PRD 回写由用户手动做，见任务三清单）；凡涉及"代码领先文档"的项（A1/D10 等）本轮不动代码。

Request（按编号执行，每项一个 commit 粒度的独立改动集合）:

【R1 = 审计 D1】资料人工创建闭环（MaterialForm.tsx + 后端 materials 接口核对）：
- 表单补 valid_from / valid_until（有效期）字段：日期选择器，非必填，提交进 payload；列表/详情已有展示则无需改。
- 恢复双动作：新增"保存草稿"（status=草稿，留在表单或回列表）与"提交审核"（status=待审核）两个按钮；编辑已有资料时按原状态走对应流转。后端创建/更新接口核对支持两种目标状态（已有能力则只改前端；后端缺参数则补）。
- 参照：资料库主PRD.md §2/§5、mvp验收清单 M01/M07、context/04 R1/R2。

【R2 = 审计 D2】资料审核权限放开（MaterialReview.tsx + 后端审核接口权限核对）：
- 移除"非管理员返回空态"的硬拦截；改为按 context/06 §2.2：成员在数据范围内且持有审核权限码即可审核（后端接口权限以 context/06 为准核对，前端移除管理员-only 判断与误导文案）。
- 文案修正：权限不足提示不得声称"context 要求管理员"。

【R3 = 审计 D3】选题每方向生成数量锁定（TopicGenerate.tsx）：
- 生成数量固定为 10（按 context/04 R4），移除 1-10 可编辑；UI 显示"每方向 10 条"说明文字。
- 若后端 count 参数已支持 1-10，不改后端（前端固定传 10 即可，保留后端弹性）。

【R4 = 审计 D4】提示词模板管理补分析类（admin/PromptTemplates.tsx）：
- task_type 下拉补齐"资料分析、数据分析"两类（对齐核心字段清单 §2 四类）。
- task_type=资料分析/数据分析 时 output_schema 字段必填（条件显示 JSON 编辑区或结构化字段输入，最小实现：JSON 文本框 + 格式校验）。
- 提交校验：分析类缺 output_schema 阻止保存。

【R5 = 审计 G3】生成页可选择已保存模板（TopicGenerate.tsx + ScriptGenerate.tsx）：
- 模板选择下拉改为请求 /api/prompt-templates?task_type=<对应类型>&status=启用（列表接口），展示全部启用模板（含内置+用户自建），不再只取 builtin 第一条。
- 选中模板 → 提交时带 prompt_template_id；"自定义提示词"模式保持现状（自定义正文优先）；不选 → 默认模板（现状行为保留）。
- 两页一致改造。

【R6 = 审计 G1】固定组合引用预览（MaterialComboField.tsx）：
- 已勾选资料下方增加"引用预览"区域（只读，Collapse 折叠默认收起）：按最终组合顺序列出每条资料的【分类】标题 + 内容前 200 字摘要（复用已加载的资料列表数据，不需新接口）。

【R7 = 任务三 文档回写】仅改以下三个文件，回写已拍板口径（这是本轮唯一允许动的文档）：
1. prd-docs/modules/数据报告/数据报告主PRD.md:331 一节："删除报告/推送记录 ❌ 默认不提供" → 改为"✅ 有限提供"，补充规则：报告删除仅限无推送记录且非生成中的报告（有推送记录=对账凭证不可删）；推送任务删除规则=已推送凭证不可删，仅待推送/失败/已取消可删（对齐 0828 已上线代码）。
2. prd-docs/modules/数据报告/推送任务取消删除与卡片跳转PRD.md:21-39：删除规则同步改为"已推送=凭证不可删"口径。
3. prd-docs/modules/数据分析/数据分析主PRD.md 与 数据分析字段清单.md：在数据源/原始数据/分析任务三处补充"删除与归档策略：待确认（当前实现为管理员直接删除，保留/关联保护规则待定稿）"——标注待确认，不发明规则。
4. prd-docs/modules/审核流程变更说明.md：加一段"⚠️ 本文件口径与 context/04 R1/R3/R6/R8 存在冲突，以 context 为准；回写待产品确认"的醒目提示（不改正文）。

Output format:
- 按编号逐项修。后端 python -m compileall -q backend/app 通过 + 前端 npm run build 通过。
- 自检报告 check-reports/PRD对齐修复-自检报告-20260828.md：逐项编号对应改动+文件+自检+遗留（含"PRD 回写仅覆盖任务三清单，全局排序/二期 P0 缺口仍为待办"）。

红线禁止:
- 禁止不执行 git pull 就改文件。
- 禁止修改 context/（任何情况）、requirements/、audit-reports/。
- prd-docs/ 仅允许任务三列出的四处回写，其余 PRD 文件禁改。
- 禁止 commit/push/deploy。
- 禁止把 draft/ 待办（全局排序、卡片折叠待办等）混入本轮实现。
- 禁止伪造构建结果。

Checkpoint:
完成后必须执行 AI 自检报告管道上传（沙箱 DNS 不解析 pmlophy.com 时按兜底规则：保存 check-reports/ + 如实汇报"未上传管道"，禁止重试超过1次）：
curl --noproxy '*' -X POST "https://pmlophy.com/p/jarvis/file/upload" -H "X-Jarvis-User: ai-reports" -F "file=@check-reports/PRD对齐修复-自检报告-20260828.md"
最后汇报：逐项编号完成状态、改动文件列表、build/compileall 结果、报告文件名与字节数、是否已上传管道。
```
