from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )
    app_name: str = "AI Agent Course API"
    api_v1_prefix: str = "/api/v1"
    app_api_key: str = "dev-api-key-123"
    llm_provider: str = "mock"
    default_model: str = "mock-chat"
    supported_models: str = "mock-chat,deepseek-chat,qwen-plus,gpt-4o-mini"
    database_url: str = "postgresql+psycopg://postgres@127.0.0.1:5432/postgres"
    cache_backend: str = "memory"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    dashscope_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    @property
    def supported_model_list(self):
        return [x.strip() for x in self.supported_models.split(",") if x.strip()]


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
