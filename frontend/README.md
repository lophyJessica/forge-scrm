# forge-scrm 前端（一期）

React 18 + TypeScript + Vite 6 + antd 5 + zustand + react-router 6。

## 1. 本地启动

```bash
cd frontend
npm install
npm run dev
```

- 开发地址：<http://localhost:5173>
- Vite 已配置代理：`/api` → `http://127.0.0.1:8000`，**先启动后端**（见 `../backend/README.md`）
- 默认账号：`admin` / `admin123`（首次登录后顶部会提示改密）

生产构建：

```bash
npm run build
```

产物在 `dist/`，部署时由后端或 Nginx 托管静态文件即可。

## 2. 目录结构

```text
frontend/src/
├── api/client.ts       axios 实例（注入 JWT、401 跳登录、统一错误提示）
├── store/
│   ├── auth.ts         登录态 + 角色/功能权限判定
│   └── meta.ts         枚举字典（统一取自 /api/meta/enums，前端不硬编码第二套）
├── layouts/            主框架（侧边菜单按角色/权限过滤）
├── components/         RequireAdmin 等通用组件
├── pages/              9 个页面组
│   ├── materials/      资料库
│   ├── topics/         选题库
│   ├── scripts/        脚本库
│   ├── analysis/       数据分析
│   └── admin/          权限账号
├── types/              后端出入参类型
└── App.tsx             路由表（一期共 28 条路由）
```

## 3. 约定

- **枚举不落地在前端**：所有状态、分类、平台等下拉选项一律通过 `useMetaStore().options(key)`
  从 `/api/meta/enums` 获取（context/05 §5）；新增枚举只改后端。
- **权限码常量**在 `src/store/meta.ts` 的 `PERM`，与后端 `app/core/enums.py` 的 `Permission` 一一对应。
- TypeScript 为 strict 模式并开启 `noUnusedLocals` / `noUnusedParameters`，构建即类型检查。
