# 面包屑首页层级修复自检报告

## 1. 现象

- 线上资料列表 `/materials` 的顶栏显示“首页 / 资料库 / 资料列表”。
- 同样的“首页”首级出现在新建资料、选题、脚本、数据分析、提示词、详情和个人账号等所有非首页页面。
- 首页自身显示“首页”，该行为保留。

## 2. 根因

- 根因文件：`frontend/src/layouts/MainLayout.tsx`。
- 根因函数：`breadcrumbItemsForPath()`，基线第 140-143 行原本固定返回 `{ title: <Link to="/">首页</Link> }`，所以所有非首页路由都会添加首页层级。
- 当前修复位置：第 135-143 行，仅返回模块父级和当前页；第 264-268 行仍让首页显示单独的“首页”标题。
- 这是统一面包屑生成逻辑的问题，不是资料列表页面单独配置、CSS 或重复渲染问题。

## 3. 改动文件

### `frontend/src/layouts/MainLayout.tsx`

- 移除非首页面包屑中的固定“首页”项。
- 保留真实路由生成的模块父级和当前页面标题。
- 保留父级点击路径，例如“资料库”返回 `/materials`，“选题库”返回 `/topics`。
- 未修改页面布局、菜单、登录、API、数据库结构或业务字段。

### `deploy/deploy.sh`

- 本轮未新增部署逻辑；沿用已迁移到搬瓦工的部署通道。
- 实际部署仍使用本地工作区、`45.78.70.160:2222`、`~/.ssh/id_ed25519` 和 `/opt/forge-scrm`。

## 4. 验证过程

### 本地

- 已执行 `git pull --ff-only origin main`，结果为 `Already up to date.`。
- `npm run build`：通过。
- Chrome 本地验证：首页仍显示“首页”；资料列表显示“资料库 / 资料列表”；其他非首页页面均不再显示“首页”。
- 已验证 `/materials`、`/materials/new`、`/materials/review`、`/topics`、`/topics/generate`、`/scripts`、`/scripts/generate`、`/analysis/tasks`、`/analysis/prompts`、详情页和 `/profile`。
- 深层路由刷新后面包屑正确。
- 点击“资料库”返回 `/materials`，后退回新建资料，前进回资料列表，均正确。

### 线上部署

- 已执行 `./deploy/deploy.sh`，最终成功退出。
- 前端实际 rsync 到 `root@45.78.70.160:2222:/opt/forge-scrm/frontend/dist/`。
- 后端实际 rsync 到 `root@45.78.70.160:2222:/opt/forge-scrm/backend/`。
- 生产 `.env` 同步前后校验一致；`.venv`、`backend/data/` 保留。
- Alembic 使用线上现有 venv 执行成功。
- `forge-scrm-api`：`active`。
- nginx：`active`。
- HTTPS 首页：`200`。
- HTTPS 登录接口：`422`。

### 线上 Chrome

- 刷新线上 `/materials` 后，视觉上显示“资料库 / 资料列表”，不再显示“首页”。
- 已逐页检查资料、选题、脚本、数据分析、详情和个人账号页面。
- 已验证线上深层路由刷新、面包屑点击、后退和前进。
- 线上标签页当前保留在 `/materials`，等待用户验收。

## 5. 部署目标

| 项目 | 值 |
|---|---|
| SSH host | `45.78.70.160` |
| SSH port | `2222` |
| SSH key | `~/.ssh/id_ed25519` |
| Remote user | `root` |
| Remote project | `/opt/forge-scrm` |
| API service | `forge-scrm-api` |
| Domain | `https://scrm.pmlophy.com` |

## 6. 遗留风险

- 后续新增路由仍需补充 `MainLayout.tsx` 中的路由标题定义，否则不会生成详细面包屑。
- Vite 仍提示 bundle 超过 500 kB；本轮未扩大范围处理。
- 详情页面包屑显示通用页面标题，不显示业务对象名称。

## 7. Git 与安全

- 未执行 git commit 或 git push。
- 报告不包含密码、token、数据库连接串或 API key。
