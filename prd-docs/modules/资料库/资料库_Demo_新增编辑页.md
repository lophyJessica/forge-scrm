# 资料库_Demo_新增编辑页

> 文件定位：资料新增/编辑页面规格
> 实现来源：`MaterialForm.tsx`
> 路由：`/materials/new`、`/materials/:id`

## 一、页面模式

| 模式 | 标题 | 数据加载 |
|---|---|---|
| 新增 | 新建资料 | 加载分类和标签 |
| 编辑 | 编辑资料 #id | 额外 GET `/materials/:id` 回填 |

## 二、表单控件

| 字段 | 控件 | 校验/交互 |
|---|---|---|
| title | Input + 字数 | 必填，≤200 |
| content | TextArea 10行 | 必填 |
| class_id | Select | 必填，来源 `/material-classes` |
| source_type | Select | 必填，meta `source_type` |
| trust_level | Select | 必填，meta `trust_level` |
| valid_range | RangePicker | 必填，提交拆为 valid_from/valid_until |
| source_url | Input | 可选，≤500 |
| tags | Select mode=tags | 可自由输入，`,` 或 `|` 分隔 |

## 三、按钮与提交

| 按钮 | 当前行为 |
|---|---|
| 存为草稿 | 新增携带 `submit_for_review=false`；编辑仅 PUT 保存 |
| 保存并提交审核 | 新增携带 true；编辑 PUT 后 POST `/submit` |
| 返回 | 回 `/materials` |

保存成功统一提示“保存成功”并返回列表。提交期间两个保存按钮共享 loading。

## 四、状态规则

- 新增存草稿：草稿。
- 新增/编辑后提交：待审核。
- 页面不提供审核动作。
- 已生效资料编辑后的再审策略 SSOT 未明确；现有页面允许编辑，需作为遗留风险处理。

## 五、Mock

```text
标题：制造业老板做短视频的三个误区
分类：商业研究结论
来源类型：报告
可信度：高
有效期：2026-08-24 ~ 2027-08-24
标签：制造业、短视频、获客
动作：保存并提交审核
```

## 六、验收

- [ ] 新增和编辑模式标题/回填正确
- [ ] 必填字段缺失时不请求接口
- [ ] 日期转换为 YYYY-MM-DD
- [ ] 自由标签可创建并保存
- [ ] 存草稿与提交审核产生不同状态
- [ ] 保存失败时 loading 恢复且保留用户输入

## 七、修订记录

| 日期 | 变更 |
|---|---|
| 2026-08-24 | 初稿：对照 MaterialForm.tsx |
