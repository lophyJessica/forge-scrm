# 数据分析_Demo_新建任务页

> 文件定位：现有 `AnalysisTasks.tsx` 内嵌“新建分析任务”Modal 规格
> 路由：`/analysis/tasks`，点击右上按钮打开

## 一、表单

| 字段 | 控件 | 规则 |
|---|---|---|
| name | Input | 可留空；前端 DTO 字段待确认 |
| type | Select | meta `analysis_task_type`，必填 |
| raw_data_ids | 多选 Select | 至少一条原始数据，必填 |
| material_ids | 多选 Select | 仅已生效资料，可空 |
| prompt_template_id | Select | 可选；排除选题/脚本模板 |

## 二、数据加载

打开 Modal 时并行加载 `/raw-data`、已生效 `/materials`、`/prompt-templates`；模板过滤掉选题生成和脚本生成类型。

## 三、提交

- 点击 Modal 确定，校验后 POST `/analysis-tasks`。
- 成功提示“任务已创建（待执行）”，关闭 Modal 并刷新列表。
- 任务初始状态为待执行。

## 四、Mock

```text
任务名称：8月账号基础分析
任务类型：数据分析
输入：#201、#202
资料上下文：#101 制造业获客研究
提示词：账号基础分析 v1
```

## 五、验收

- [ ] 无原始数据不能创建
- [ ] 未生效资料不出现在选择器
- [ ] 任务类型来自 meta，不硬编码第二套
- [ ] 创建成功后列表显示待执行

## 六、修订记录

| 日期 | 变更 |
|---|---|
| 2026-08-24 | 初稿：对照 AnalysisTasks.tsx 新建任务 Modal |
