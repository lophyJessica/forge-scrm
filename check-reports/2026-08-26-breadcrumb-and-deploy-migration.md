# 面包屑与部署迁移自检报告

## 1. 现象

- 本地 Chrome 登录后首页顶栏显示“首页”；访问 `/materials/new` 时显示原始路径 `/materials/new`，与截图一致。
- `/topics/generate`、资料审核、脚本版本、分析任务详情、个人账号等页面也直接显示 pathname。
- 刷新深层路由后该现象仍存在；没有独立的 Breadcrumb 页面组件，页面文件也没有重复手写面包屑。

## 2. 根因

- 根因文件：`frontend/src/layouts/MainLayout.tsx`。
- 根因组件/位置：`MainLayout` 顶栏原实现，基线第 194-200 行；其中第 199 行直接渲染 `location.pathname`，没有根据 `App.tsx` 的真实路由生成页面标题、父级层级或点击路径。
- `frontend/src/App.tsx` 第 34-83 行定义了实际路由，但原 `MainLayout` 没有消费这些路由的标题信息，因此出现“路由数据存在、展示层级缺失”的问题。
- 已排除：不是 CSS 布局、组件重复渲染或页面标题样式问题；截图中的异常文本就是内部 pathname。

## 3. 改动文件

### `frontend/src/layouts/MainLayout.tsx`

- 将侧边菜单的路径和中文标题整理为统一的 `NAV_GROUPS` 路由定义，菜单和面包屑共用这套数据。
- 新增集中式详情路由匹配，覆盖资料、选题、脚本版本、分析任务详情和个人账号页。
- 新增 `routeDefinitionForPath()` 与 `breadcrumbItemsForPath()`，面包屑由当前真实 `location.pathname` 生成。
- 顶栏使用 Ant Design `Breadcrumb`；首页仍只显示“首页”，不增加多余层级。
- 首页、模块父级均可点击；模块父级返回对应列表页，例如“资料库”返回 `/materials`，“选题库”返回 `/topics`。
- 未修改页面布局、左侧菜单行为、登录逻辑、API 逻辑或后端契约。

### `deploy/deploy.sh`

- 部署目标改为 `root@45.78.70.160:2222:/opt/forge-scrm`。
- SSH key 固定为 `~/.ssh/id_ed25519`，移除旧 key 自动探测。
- 保留本地工作区为准的部署方式，不执行 `git pull`。
- 前端从本地 `frontend/dist/` 使用 rsync 同步；后端从本地 `backend/` 使用 rsync 同步。
- 后端同步排除 `.env`、`.venv`、`.venv*`、缓存、`*.pyc`、`data/`、`*.db` 和 `.DS_Store`。
- 同步前后通过远端 `.env` sha256 做保护校验；线上 `.env` 未被覆盖。
- Alembic 使用 `/opt/forge-scrm/backend/.venv/bin/python -m alembic upgrade head`，并先进入远端 backend 目录。
- 重启并检查 `forge-scrm-api` 与 nginx；最终验证改为 HTTPS 首页和登录接口。

## 4. 验证过程

### 本地代码与浏览器

- 已执行 `git pull --ff-only origin main`：`Already up to date.`
- `npm run build`：通过；Vite 仅提示现有 bundle 超过 500 kB 的优化建议。
- 本地 Chrome 登录后验证：首页、`/topics/generate`、资料审核、资料新建、脚本版本、分析任务详情、权限管理、个人账号。
- 本地深层路由刷新后面包屑保持正确。
- 本地点击“资料库”返回 `/materials`；浏览器后退回 `/materials/new`、前进回 `/materials`，面包屑均正确。
- 本地截图视觉确认：`/materials/new` 显示“首页 / 资料库 / 新建资料”，不再显示 `/materials/new`。

### 部署与线上

- 已实际执行 `./deploy/deploy.sh`，最终成功退出。
- 首轮执行曾在 Alembic 工作目录处停止，未重启服务；已修正为先进入 `/opt/forge-scrm/backend` 后重新执行，第二轮完整成功。
- 前端 rsync 实际目标：`root@45.78.70.160:2222:/opt/forge-scrm/frontend/dist/`。
- 后端 rsync 实际目标：`root@45.78.70.160:2222:/opt/forge-scrm/backend/`。
- 远端 `.env`、`.venv`、`backend/data/` 均存在；MySQL 业务数据未被 rsync 覆盖或重建。
- Alembic 使用线上 MySQL 通过。
- `forge-scrm-api`：`active`。
- nginx：`active`。
- HTTPS 首页：`200`。
- HTTPS 登录接口：`422`，接口可达。
- 未执行 git commit、git push；当前仅保留本轮两个源码文件的未提交修改。

### 线上 Chrome

- 已刷新线上 `/materials/new`，确认显示“首页 / 资料库 / 新建资料”。
- 已访问 `/topics/generate`，确认显示“首页 / 选题库 / 批量生成”。
- 已验证资料审核、脚本版本、分析任务详情、个人账号等页面的中文层级。
- 已验证线上深层路由刷新、面包屑点击、后退和前进。
- 线上 Chrome 标签页当前保留在 `/materials/new`，等待用户浏览器验收。

## 5. 部署目标

| 项目 | 最终值 |
|---|---|
| SSH host | `45.78.70.160` |
| SSH port | `2222` |
| SSH key | `~/.ssh/id_ed25519` |
| Remote user | `root` |
| Remote project | `/opt/forge-scrm` |
| API service | `forge-scrm-api` |
| Domain | `https://scrm.pmlophy.com` |

旧 Lisa IP、旧 key、HTTP 域名和旧远端路径均未保留在 `deploy/deploy.sh` 的可执行逻辑中。

## 6. 遗留风险

- 后续如果在 `App.tsx` 新增路由，需要同时在 `MainLayout.tsx` 的统一菜单/详情路由定义中补充标题，否则该新路由不会产生详细面包屑；当前未知路径不会退回显示原始 pathname。
- Vite 构建仍有 bundle 超过 500 kB 的性能提示，本轮未扩大范围处理。
- 面包屑中文标题是路由元数据，不会读取详情对象名称；例如详情页显示“选题详情”或“分析任务详情”，不显示业务对象标题。
