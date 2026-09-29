"""从当前模块旁的 .env 加载配置，系统环境变量优先。"""

import os
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, SecretStr

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"


class AgentConfig(BaseModel):
    api_key: SecretStr
    tavily_api_key: SecretStr = SecretStr("")
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"


def get_config() -> AgentConfig:
    env_values = dotenv_values(ENV_PATH)

    def get_value(key_name: str, default: str = "") -> str:
        return os.environ.get(key_name, env_values.get(key_name) or default).strip()

    api_key = get_value("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("缺少 DEEPSEEK_API_KEY，请在 src/.env 或系统环境变量中配置")

    return AgentConfig(
        api_key=SecretStr(api_key),
        tavily_api_key=SecretStr(get_value("TAVILY_API_KEY")),
        base_url=get_value("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        model=get_value("DEEPSEEK_MODEL", "deepseek-chat"),
    )
