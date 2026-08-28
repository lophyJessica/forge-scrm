"""应用配置：统一从环境变量 / .env 读取，禁止硬编码任何密钥。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    app_name: str = "forge-scrm"
    app_env: str = "local"
    log_level: str = "INFO"

    # 数据库：本地 SQLite 兼容模式；VPS 部署切 MySQL（见 README）
    database_url: str = "sqlite:///./data/forge_scrm.db"

    # JWT（D-T5：24h 有效期，不做 refresh token）
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # 种子管理员账号（首次启动创建；README 注明首次登录须改密）
    seed_admin_username: str = "admin"
    seed_admin_password: str = "admin123"

    # DeepSeek（key 只能来自环境变量）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout: int = 120
    deepseek_max_retry: int = 3

    # 研究助手检索（key 只能来自环境变量 TAVILY_API_KEY；供应商可替换）
    tavily_api_key: str = ""
    tavily_base_url: str = "https://api.tavily.com/search"
    tavily_timeout: int = 30

    # 飞书企业自建应用推送（凭据只从环境变量读取）
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_push_open_ids: str = ""

    # 本地文件存储（D-T4）
    data_dir: str = "./data"

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def data_path(self) -> Path:
        p = Path(self.data_dir)
        if not p.is_absolute():
            p = BACKEND_ROOT / p
        return p

    @property
    def csv_path(self) -> Path:
        return self.data_path / "csv"

    @property
    def ai_raw_path(self) -> Path:
        return self.data_path / "ai_raw"

    @property
    def sqlalchemy_url(self) -> str:
        """相对路径的 SQLite 统一挂到 backend 根目录，避免工作目录不同导致多个库文件。"""
        url = self.database_url
        prefix = "sqlite:///./"
        if url.startswith(prefix):
            return f"sqlite:///{BACKEND_ROOT / url[len(prefix):]}"
        return url

    @property
    def is_sqlite(self) -> bool:
        return self.sqlalchemy_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_path.mkdir(parents=True, exist_ok=True)
    settings.csv_path.mkdir(parents=True, exist_ok=True)
    settings.ai_raw_path.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
