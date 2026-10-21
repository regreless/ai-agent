from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    app_name: str = "Enterprise AI Agent Platform Real"
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me-please"
    access_token_expire_minutes: int = 1440
    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8501,http://127.0.0.1:8501"

    database_url: str = "postgresql+asyncpg://agent_user:agent_password@localhost:5432/agent_db"
    sync_database_url: str = "postgresql+psycopg://agent_user:agent_password@localhost:5432/agent_db"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "enterprise_agent_chunks"
    vector_dim: int = 1024

    llm_provider: str = "deepseek"
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    deepseek_timeout_seconds: float = 30

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:0.8b"

    embedding_provider: str = "zhipu"
    qwen_embedding_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    qwen_embedding_api_key: str = os.getenv("ZHIPUAI_API_KEY", "")
    qwen_embedding_model: str = "embedding-3"
    qwen_embedding_dim: int = 1024

    upload_dir: str = "/src/uploads"
    mcp_order_command: str = "python"
    mcp_order_args: str = "/src/mcp_servers/order_server.py"

    default_admin_email: str = "admin@example.com"
    default_admin_password: str = "admin123456"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_list(self) -> list[str]:
        return [item.strip() for item in self.backend_cors_origins.split(',') if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
