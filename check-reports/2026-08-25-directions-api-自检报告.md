# forge-scrm directions 后端接口补齐自检报告

## 1. 任务摘要

- 项目：Forge 新媒体运营系统（forge-scrm）
- 日期：2026-08-25
- 任务：补齐选题生成页所需的 `GET/POST /api/directions*` 后端接口，消除前端 404 Not Found
- 依据：选题库字段清单 §一 business_direction、§二 specialty（即建即用 + 二级联动）
- 约束：未改 topic 表结构、未改前端、未改 context/prd-docs/requirements

## 2. 新增/改动文件清单

| 文件 | 类型 | 改动点 |
|---|---|---|
| `backend/app/models/direction.py` | 新增 | `BusinessDirection`、`Specialty` ORM；status 枚举 active/inactive |
| `backend/app/schemas/direction.py` | 新增 | Out/Create/Response Pydantic 模型，字段名与前端一致 |
| `backend/app/routers/directions.py` | 新增 | GET 全量、POST business、POST specialties；CurrentUser 权限 |
| `backend/app/models/__init__.py` | 修改 | 导出 BusinessDirection、Specialty |
| `backend/app/main.py` | 修改 | 注册 directions router |
| `backend/alembic/versions/a3f8c2d91e4b_add_direction_tables.py` | 新增 | 创建 business_direction + specialty 表及唯一约束 |
| `deploy/deploy.sh` | 修改 | rsync 后端增加 `--exclude='.env'` |

## 3. 接口清单

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/directions` | 返回 `{business_directions, specialties}`，仅 status=active |
| POST | `/api/directions/business` | body `{name}`，重名 BizError 400 |
| POST | `/api/directions/specialties` | body `{business_direction_id,name}`，组内重名 BizError 400 |

## 4. 本地验证结果

| 项 | 结果 |
|---|---|
| `alembic upgrade head` | ✅ 成功（1c1a51600ffc → a3f8c2d91e4b） |
| SQLite 表 | ✅ `business_direction`、`specialty` 已创建 |
| GET `/api/directions` | ✅ HTTP 200，含两个数组字段 |
| POST `/api/directions/business` | ✅ HTTP 200，创建「制造业获客」 |
| POST `/api/directions/specialties` | ✅ HTTP 200，创建「短视频获客」 |
| `npm run build` | ✅ 通过 |

## 5. 遗留风险

1. `topic.direction` / `topic.specialty` 仍为字符串/枚举列，与方向表无 FK；生成时按名称写入，需保持前后端名称一致
2. 专业方向表 `name` 与 topic 生成 API 的 `Specialty` 枚举仍为两套口径；前端用 specialty.name 作 enumValue 兜底提交
3. 一期未实现方向停用（inactive）与删除接口
4. POC 部署后须确认 `alembic upgrade head` 在 MySQL 上执行成功

## 6. 红线遵守

- 未 commit / push
- 未修改前端、topic 表、业务文档
- 未在报告/代码中写入密钥或 token
