"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger, setup_logging
from app.services.seed import run_seed

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()
    logger.info("%s 启动完成（env=%s）", settings.app_name, settings.app_env)
    yield


app = FastAPI(
    title="Forge 新媒体运营系统 API",
    description="forge-scrm 一期后端（资料库 / 选题库 / 脚本库 / 数据分析 / 权限账号）",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["系统"], summary="健康检查")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


def _register_routers() -> None:
    from app.routers import (
        analysis,
        auth,
        materials,
        meta,
        prompts,
        scripts,
        topics,
        users,
    )

    for module in (auth, users, meta, materials, topics, scripts, analysis, prompts):
        app.include_router(module.router)


_register_routers()
