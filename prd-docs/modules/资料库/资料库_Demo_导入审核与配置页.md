# 资料库_Demo_导入审核与配置页

> 文件定位：资料库辅助页面合并规格
> 覆盖实现：MaterialImport.tsx / MaterialReview.tsx / MaterialClasses.tsx / Tags.tsx

## 一、批量导入 `/materials/import`

页面标题“资料批量导入（CSV / TXT）”，包含说明 Alert、下载模板、上传文件和导入结果区。

| 控件 | 行为 |
|---|---|
| 下载导入模板 | GET `/materials/csv-template`，下载 `material_import_template.csv` |
| 选择文件并导入 | 接受 `.csv,.txt`，POST `/materials/import` |
| 结果摘要 | total_rows/success/failed/stored_file |
| 错误表 | 失败时展示 row/message |

现有说明明确：成功资料进入待审核，必填列和标签 `|` 分隔规则见业务规则规格。

## 二、资料审核 `/materials/review`

| 区域 | 当前实现 |
|---|---|
| 数据 | 查询 status=待审核，page_size=100 |
| 列 | ID、标题、AI标记、分类、可信度、有效期、操作 |
| 展开行 | 展示完整正文 |
| 操作 | 通过→已生效；驳回→已废弃 |

实现差异：组件当前将非管理员拦为 Empty，但 `context/06` 允许成员在数据范围内审核。Demo 记录现状，开发规则以 SSOT 为准。

## 三、分类管理 `/material-classes`

- 表格：ID、分类名、父级 id、排序、操作。
- 管理员可新建/编辑/删除；非管理员只读。
- Modal 字段：name 必填，parent_id 可选，sort 可选。
- `sort` 为 ⚠️ 新增建议，待确认。

## 四、标签管理 `/tags`

- 标题注明自由创建、标签组可选。
- 有 `PERM.标签创建` 时显示行内新建表单：name 必填、group_name 可选。
- 支持关键词搜索；表格列 ID、标签名、标签组。
- 当前无编辑/删除标签交互。

## 五、Mock

```text
导入：总5行，成功4，失败1（第3行“分类不存在”）
审核：#201 [AI产物] 咨询下降原因 → 通过
分类：商业研究结论 / 父级— / 排序1
标签：制造业 / 标签组—
```

## 六、验收

- [ ] 导入模板可下载，CSV/TXT 可上传
- [ ] 导入失败行准确展示且成功行保留
- [ ] 审核队列只含待审核资料
- [ ] 分类操作仅管理员可见
- [ ] 标签组为空仍可创建标签
- [ ] 权限实现差异已纳入开发走查

## 七、修订记录

| 日期 | 变更 |
|---|---|
| 2026-08-24 | 初稿：合并覆盖资料导入、审核、分类和标签四个现有页面 |
