# 权限账号_Demo_成员编辑页

> 文件定位：现有 `Users.tsx` 新增/编辑成员与重置密码 Modal 规格
> 路由：`/admin/users` 内嵌 Modal

## 一、新增成员 Modal

| 字段 | 控件 | 规则 |
|---|---|---|
| username | Input | 新增显示，必填，最少2位，≤100 |
| password | Password | 新增显示，必填，最少6位，≤128 |
| role | Select | 管理员/成员，必填 |
| functional_permissions | Checkbox.Group | 权限项由 `/meta/permissions` 加载 |
| scope_type | Select | 全量/指定，必填 |
| material_class_ids | 多选 | scope_type=指定时显示 |
| data_source_ids | 多选 | scope_type=指定时显示 |

提交 POST `/users`，保存后刷新成员列表。

## 二、编辑成员 Modal

- 标题为“编辑 username”。
- username/password 隐藏，只提交 role、functional_permissions、data_scope。
- 编辑已有数据范围时回填资料分类和数据源。
- 切换范围类型由 `scopeType` 控制指定范围字段显隐。

## 三、重置密码 Modal

- 标题为“重置 username 的密码”。
- 新密码 Password，最少6位，最多128位。
- 提交 POST `/users/:id/reset-password`，成功提示“密码已重置”。

## 四、Mock

```text
新增成员
账号：editor
初始密码：••••••••
角色：成员
功能权限：资料查看、选题筛选
数据范围：指定
可见资料分类：商业研究结论
可见数据源：视频号-自己
```

## 五、验收

- [ ] 管理员可新增成员且账号密码必填
- [ ] 成员角色/权限/数据范围保存正确
- [ ] 指定范围才显示分类/数据源多选
- [ ] 编辑不允许修改账号字段（当前页面行为）
- [ ] 重置密码后成功提示，密码不回显
- [ ] 不设置业务成员数量上限

## 六、实现差异

权限码列表由后端 `/meta/permissions` 返回，具体成员动作仍受 context/06 待确认矩阵约束；页面勾选项不等于业务方已确认全部授权。

## 七、修订记录

| 日期 | 变更 |
|---|---|
| 2026-08-24 | 初稿：对照 Users.tsx 成员编辑和重置密码 Modal |
