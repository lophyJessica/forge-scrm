# Forge SCRM「批量生成」白屏修复自检报告

## 1. 任务 / 项目

- 项目：forge-scrm（Forge 新媒体运营系统）
- 任务：排查进入首页与 `/topics/generate` 后 React 白屏，修复根因并部署 POC。
- 执行日期：2026-08-25
- 代码基线：执行 `git pull origin main`，结果为 `Already up to date.`

## 2. 白屏根因与完整浏览器报错

### 根因

`frontend/src/pages/topics/TopicGenerate.tsx` 原第 54 行在 Zustand selector 内调用了 `s.options('specialty')`。`options()` 每次都会创建新数组，Zustand v5 通过 `useSyncExternalStore` 获取快照时发现结果不稳定，触发无限重渲染，最终 React 无法挂载 `TopicGenerate`，页面内容区为空白。

### 本地 Chrome 复现的原始控制台报错

```text
Warning: The result of getSnapshot should be cached to avoid an infinite loop%s
    at TopicGenerate (http://127.0.0.1:5173/src/pages/topics/TopicGenerate.tsx:52:23)
    at RenderedRoute (http://127.0.0.1:5173/node_modules/.vite/deps/react-router-dom.js?v=20235910:4112:5)
    at Outlet (http://127.0.0.1:5173/node_modules/.vite/deps/react-router-dom.js?v=20235910:4518:26)
    at main
    at Content
    at Layout
    at MainLayout (http://127.0.0.1:5173/src/layouts/MainLayout.tsx:50:64)
    at RenderedRoute
    at Routes
    at App
    at Router
    at BrowserRouter
    at div
    at App
    at LocaleProvider
    at MotionWrapper
    at ProviderChildren
    at ConfigProvider
```

```text
Error: Maximum update depth exceeded. This can happen when a component repeatedly calls setState inside componentWillUpdate or componentDidUpdate. React limits the number of nested updates to prevent infinite loops.
    at checkForNestedUpdates (http://127.0.0.1:5173/node_modules/.vite/deps/chunk-NXESFFTV.js?v=20235910:19712:19)
    at scheduleUpdateOnFiber (http://127.0.0.1:5173/node_modules/.vite/deps/chunk-NXESFFTV.js?v=20235910:18583:11)
    at forceStoreRerender (http://127.0.0.1:5173/node_modules/.vite/deps/chunk-NXESFFTV.js?v=20235910:12047:13)
    at updateStoreInstance (http://127.0.0.1:5173/node_modules/.vite/deps/chunk-NXESFFTV.js?v=20235910:12023:11)
    at commitHookEffectListMount (http://127.0.0.1:5173/node_modules/.vite/deps/chunk-NXESFFTV.js?v=20235910:16963:11)
    at commitPassiveMountOnFiber (http://127.0.0.1:5173/node_modules/.vite/deps/chunk-NXESFFTV.js?v=20235910:18206:11)
    at flushPassiveEffectsImpl (http://127.0.0.1:5173/node_modules/.vite/deps/chunk-NXESFFTV.js?v=20235910:19543:13)
```

```text
The above error occurred in the <TopicGenerate> component:
    at TopicGenerate (http://127.0.0.1:5173/src/pages/topics/TopicGenerate.tsx:52:23)
```

首页本地复现正常，说明全局挂载、路由守卫和 `MainLayout` 不是白屏根因。

## 3. 改动文件与改动点

### `frontend/src/pages/topics/TopicGenerate.tsx`

- 第 54-55 行：改为先通过稳定 selector 取 `s.options` 函数，再在组件体内调用 `options('specialty')`，避免 selector 返回新数组导致无限渲染。
- 第 91-100 行：方向接口返回的专业方向只有展示名称时，按既有静态方向映射恢复 SSOT 专业枚举值；未知新增专业方向使用既有默认枚举“市场营销”。不改后端表结构、不新增业务枚举。

## 4. 构建与本地验证

- `npm run build`：通过。
- 最终本地构建产物：`frontend/dist/assets/index-CerYtq81.js`，CSS 为 `index-BzDNEqOL.css`。
- 旧线上产物 `index-CvOXUbjJ.js` 与本次构建 hash 不同，说明 dist 已包含修复后的新代码。
- Chrome 本地 `http://127.0.0.1:5173/`：正常挂载首页，无 error 日志。
- Chrome 本地 `http://127.0.0.1:5173/topics/generate`：正常挂载，无 `getSnapshot` / `Maximum update depth exceeded`。
- 方向下拉：可打开、可选择“制造业获客”。
- 二级联动：选择业务方向后专业方向可用，可选择“短视频获客”。
- 新增方向：可打开“新增业务方向”并新增“本地验收方向”。该联调数据保留，未删除。
- 生成按钮：表单完整时可用，请求链路已发出；本地环境因 `backend/.env` 未配置 DeepSeek key 返回业务错误，页面仍保持挂载，无 React 对象渲染崩溃。

## 5. 线上部署与验证

执行：

```bash
cd /Users/liulongfei/个人文件/forge-scrm && ./deploy/deploy.sh
```

部署脚本结果：

- 前端 dist 同步完成。
- 后端源码同步完成，`.env` 已按脚本排除。
- `forge-scrm-api`、MySQL、nginx 均为 active。
- Alembic MySQL 升级检查完成。
- HTTP 首页：200。
- HTTP `/topics/generate`：200。
- HTTP 登录探测：422（接口可达，符合脚本预期）。
- HTTP 首页引用：`assets/index-CerYtq81.js`。
- HTTP 新 JS 资源：200。

### Chrome 线上限制

部署后使用 Chrome 新标签页访问 `https://scrm.pmlophy.com/` 与 `http://scrm.pmlophy.com/`，浏览器均返回 `ERR_CONNECTION_CLOSED`，没有进入应用 DOM，因此无法从 Chrome 获取线上页面渲染结果或线上 JS 控制台。终端对 HTTPS 的 curl 也返回 `SSL_ERROR_SYSCALL`；HTTP 入口已验证 200。该项需路飞在当前网络/Chrome 会话中打开线上 HTTP 入口复核。

## 6. 遗留风险

- Chrome 当前网络链路无法访问线上域名的 HTTPS，线上浏览器确认未完成；HTTP curl 与部署脚本验证已通过。
- 本地 `.env` 未配置 DeepSeek key，未执行真实 AI 生成；未修改 `.env`。
- antd 仍输出已有的 `dropdownRender` 弃用警告和静态 `message` context 警告，但不影响页面挂载；本次未扩大修复范围。
- 未执行 commit / push。
