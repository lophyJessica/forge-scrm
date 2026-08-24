# forge-scrm 后端（一期）

Forge 新媒体运营系统一期后端：FastAPI + SQLAlchemy 2.x + Alembic。
本地开发用 SQLite（兼容模式），**DDL 以 MySQL 为标准**，VPS 部署时只换 `DATABASE_URL` 即切 MySQL。

## 1. 环境要求

- Python 3.11+
- Node 18+（前端，见 `../frontend/README.md`）
- MySQL 8.0（仅 VPS 部署需要，本地不需要）

## 2. 本地启动

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # 然后按第 4 节填写变量（至少填 JWT_SECRET / DEEPSEEK_API_KEY）
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8000
```

启动后：

- API 根路径：<http://127.0.0.1:8000/api>
- 健康检查：<http://127.0.0.1:8000/api/health>
- 接口文档（Swagger）：<http://127.0.0.1:8000/docs>

首次启动会自动执行种子数据（幂等）：

- 创建管理员账号：`SEED_ADMIN_USERNAME` / `SEED_ADMIN_PASSWORD`，默认 **admin / admin123**；
  登录响应会返回 `must_change_password=true`，前端顶部提示改密，**请首次登录后立即修改**。
- 写入 6 个资料分类（商业研究结论 / 案例包装 / 评论和私信 / 个人观点 / 对标账号分析 / 相关热点）。

## 3. 目录结构

```text
backend/
├── alembic/                 数据库迁移（versions/ 下为 17 张表的初始迁移）
├── app/
│   ├── core/                配置、数据库、日志、鉴权、枚举、异常
│   ├── models/              SQLAlchemy 模型（17 张表）
│   ├── schemas/             Pydantic 出入参
│   ├── services/            业务服务（资料/选题/脚本/分析/DeepSeek/种子）
│   ├── routers/             API 路由（8 个路由文件）
│   └── main.py              应用入口
├── data/                    本地文件存储（D-T4；已被 .gitignore 排除）
│   ├── csv/                 CSV 导入原文件留档
│   └── ai_raw/              AI 原始响应留档（S04）
├── scripts/
│   ├── selftest_mvp.py      MVP 验收清单 Must 45 条本地自测脚本
│   └── selftest_result.md   最近一次自测结果
└── requirements.txt
```

## 4. 环境变量

| 变量 | 说明 | 本地默认 |
| --- | --- | --- |
| `APP_NAME` | 应用名 | `forge-scrm` |
| `APP_ENV` | 运行环境标识 | `local` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `DATABASE_URL` | 数据库连接串 | `sqlite:///./data/forge_scrm.db` |
| `JWT_SECRET` | JWT 签名密钥，**生产必须替换为随机长串** | `change-me-in-production` |
| `JWT_ALGORITHM` | 签名算法 | `HS256` |
| `JWT_EXPIRE_HOURS` | token 有效期（D-T5：24h，过期重新登录，无 refresh token） | `24` |
| `SEED_ADMIN_USERNAME` | 种子管理员账号 | `admin` |
| `SEED_ADMIN_PASSWORD` | 种子管理员初始密码（bcrypt 入库） | `admin123` |
| `DEEPSEEK_API_KEY` | DeepSeek key，**只允许经环境变量注入，禁止硬编码** | 空（必须自行填写） |
| `DEEPSEEK_BASE_URL` | DeepSeek 接口地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型名 | `deepseek-chat` |
| `DEEPSEEK_TIMEOUT` | 单次请求超时（秒） | `120` |
| `DEEPSEEK_MAX_RETRY` | 失败重试次数（指数退避） | `3` |
| `DATA_DIR` | 本地文件存储根目录（D-T4） | `./data` |
| `CORS_ORIGINS` | 允许跨域来源，逗号分隔 | `http://localhost:5173,http://127.0.0.1:5173` |

生成随机 JWT 密钥：

```bash
python3 -c "import secrets;print(secrets.token_urlsafe(48))"
```

> `.env` 已被根目录 `.gitignore` 排除。**任何密钥都不得写进源码或提交进仓库。**

## 5. SQLite → MySQL 迁移（VPS 部署）

一期本地用 SQLite 只为开发方便，所有模型的 DDL 都按 MySQL 标准编写（`utf8mb4`、`VARCHAR` 长度显式声明、
枚举以字符串列 + 应用层枚举校验实现），切换只需两步：

1. 在 MySQL 上建库（字符集必须 `utf8mb4`）：

   ```sql
   CREATE DATABASE forge_scrm DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'forge'@'127.0.0.1' IDENTIFIED BY '<强密码>';
   GRANT ALL PRIVILEGES ON forge_scrm.* TO 'forge'@'127.0.0.1';
   FLUSH PRIVILEGES;
   ```

2. 修改 `.env` 后重新执行迁移：

   ```bash
   # .env
   DATABASE_URL=mysql+pymysql://forge:<强密码>@127.0.0.1:3306/forge_scrm?charset=utf8mb4
   ```

   ```bash
   .venv/bin/alembic upgrade head
   ```

启动时种子数据会在新库重新执行，管理员账号与资料分类自动补齐。
本地 SQLite 里的开发数据**不做**自动迁移（都是测试数据，无需带到生产）。

依赖已包含 `PyMySQL`，无需额外安装驱动。

## 6. 本地自测

```bash
cd backend
.venv/bin/python scripts/selftest_mvp.py
```

脚本使用**独立临时 SQLite 库**（不污染开发库），对 DeepSeek 调用打桩，逐条跑 MVP 验收清单
Must 45 条，结果写入 `scripts/selftest_result.md`，有失败项时以退出码 1 结束。

> 打桩只验证「提示词组装 / 结构化校验 / 留档 / 去重 / 状态流转 / 失败重试与留痕」的完整代码路径；
> **真实 DeepSeek 连通性需配置有效 `DEEPSEEK_API_KEY` 后另行验证。**

## 7. 一期未实现（按方案明确不做，仅预留结构）

自动采集逻辑、定时任务、语义去重、扫码/验证码登录、选题版本表、深度分析指标、对象存储。
`data_source` 表已建但不含采集实现；有效期过期为惰性判断（D-T3），无定时扫描任务。
