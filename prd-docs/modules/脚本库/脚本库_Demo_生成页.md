# 脚本库_Demo_生成页

> 文件定位：现有 `ScriptGenerate.tsx` 页面规格
> 路由：`/scripts/generate`，可通过 `/scripts/generate?topic_id=` 预选题

## 一、页面结构

```text
Card：基于选题生成脚本
├─ 同步生成提示 Alert
├─ 来源选题 Select（仅已选定）
├─ 语言风格 Select
├─ 内容要素 Select 多选
├─ 生成版数 InputNumber（2-3，默认3）
├─ 参考资料 Select 多选（仅已生效）
├─ 提示词模板 Select（可选）
└─ 开始生成
结果 Card：生成版数、表格、AI 原始响应留档、查看按钮
```

## 二、实际交互

- 页面加载：分别请求已选定选题、已生效资料、脚本生成模板。
- URL 的 `topic_id` 自动写入来源选题字段。
- 点击生成：同步 POST `/scripts/generate`，按钮 loading。
- 成功：显示生成版数、脚本摘要、版本、状态和 `ai_raw_archive`；可查看详情。
- 失败：由全局拦截器提示，loading 恢复。

## 三、字段与枚举

| 表单项 | 来源 |
|---|---|
| topic_id | 仅已选定 TopicOut |
| style | meta `script_style` |
| content_elements | meta `content_element` |
| version_count | 2-3 |
| material_ids | status=已生效资料 |
| prompt_template_id | task_type=脚本生成 |

## 四、Mock

```text
来源选题：#101 制造业获客的三个误区
语言风格：讲故事
内容要素：案例、数据、个人观点
生成版数：3
结果：3版脚本，状态=草稿，AI原始响应=/archive/scripts/301.json
```

## 五、验收

- [ ] 非已选定选题不出现在下拉
- [ ] 版数只能为 2-3
- [ ] 只显示已生效资料
- [ ] URL topic_id 可自动带入
- [ ] 结果列表可进入详情
- [ ] 同步执行期间防重复提交

## 六、修订记录

| 日期 | 变更 |
|---|---|
| 2026-08-24 | 初稿：对照 ScriptGenerate.tsx |
