# Forge SCRM 资料库菜单保持展开修复自检报告

## 1. 任务 / 项目

- 项目：forge-scrm（Forge 新媒体运营系统）
- 任务：修复资料库菜单下点击“分类管理”“标签管理”后，资料库一级菜单子项自动收起的问题。
- 执行日期：2026-08-25
- 代码基线：已执行 `git pull origin main`，结果为 `Already up to date.`

## 2. 复现与根因

本地 Chrome 访问资料审核页并展开侧边栏后，点击“分类管理”：

- URL 正确切换到 `/material-classes`。
- 侧边栏整体仍为展开状态（顶栏图标为 `menu-fold`）。
- 但“资料库”一级菜单子项消失。

点击“标签管理”同样复现，URL 切换到 `/tags` 后子项被收起。

根因是 `frontend/src/layouts/MainLayout.tsx` 原 `parentKeyForPath()` 只按一级菜单 key 的路径前缀判断。`/materials/review` 能匹配 `materials`，但 `/material-classes` 和 `/tags` 不以 `/materials` 开头，路由变化后副作用将 `openKeys` 设置为空，导致资料库子菜单收起。

## 3. 改动文件与改动点

### `frontend/src/layouts/MainLayout.tsx`

- 第 32-44 行：新增 `MenuGroup` 类型，让父菜单判断可以读取子菜单路径。
- 第 37-44 行：`parentKeyForPath()` 改为同时匹配一级菜单路径和子菜单路径，因此 `/material-classes`、`/tags` 都能映射回 `materials`。
- 第 130-137 行：路由变化时基于完整 `moduleItems` 计算父菜单，不再只传一级菜单 key 列表。
- 未修改业务规则、字段枚举、后端表结构、`.env`。

## 4. 构建与本地 Chrome 验证

- `npm run build`：通过。
- 构建产物：`frontend/dist/assets/index-ChRUjuYk.js`，CSS 为 `index-BzDNEqOL.css`。
- 本地 Chrome 验证结果：
  - `/materials/review` → 点击“分类管理”：资料库一级菜单保持展开。
  - `/material-classes` → 点击“标签管理”：资料库一级菜单保持展开。
  - `/tags` → 点击“资料审核”：资料库一级菜单保持展开。
  - 再次点击“分类管理”：资料库一级菜单保持展开。
- 上述三条路由切换均正常渲染，Chrome 控制台无 error。
- 未执行删除操作，未新增业务数据。

## 5. 线上部署与验证

执行：

```bash
cd /Users/liulongfei/个人文件/forge-scrm && ./deploy/deploy.sh
```

部署脚本结果：

- 前端 dist 同步完成。
- 后端源码同步完成，`.env` 按脚本排除。
- `forge-scrm-api`、MySQL、nginx 均为 active。
- Alembic MySQL 升级检查完成。
- HTTP 首页：200。
- HTTP `/materials/review`：200。
- HTTP `/material-classes`：200。
- HTTP `/tags`：200。
- HTTP 登录探测：422（接口可达，符合脚本预期）。
- 首页引用 `assets/index-ChRUjuYk.js`，资源响应 200。

## 6. Chrome 线上限制与遗留风险

- 部署后 Chrome 访问 `http://scrm.pmlophy.com/materials/review` 自动进入 HTTPS 后仍返回 `ERR_CONNECTION_CLOSED`，未能从 Chrome 获取线上 DOM；终端 HTTP curl 已验证上述路由均 200。
- 本次未执行 commit / push。
- 仓库中此前已有的后端方向接口、部署脚本、TopicGenerate 修复及上一份自检报告均保留，未覆盖或回退。
