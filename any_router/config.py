"""配置管理 — 从环境变量加载配置。"""

import os
from pathlib import Path

from dotenv import load_dotenv

from any_router.exceptions import ConfigError

# 加载 .env 文件（从当前目录逐级向上查找）
load_dotenv()


def _get_data_dir() -> Path:
    """获取数据存储目录，不存在则创建。"""
    custom_dir = os.getenv("ANY_ROUTER_DATA_DIR")
    if custom_dir:
        data_dir = Path(custom_dir)
    else:
        data_dir = Path.home() / ".any_router" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


class Settings:
    """应用配置。"""

    # DeepSeek API
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv(
        "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
    )
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # 路径
    DATA_DIR: Path = _get_data_dir()
    DB_PATH: Path = DATA_DIR / "any_router.db"

    @classmethod
    def validate(cls) -> None:
        """校验必要配置，缺失则抛 ConfigError。"""
        if not cls.DEEPSEEK_API_KEY:
            raise ConfigError(
                "未设置 DEEPSEEK_API_KEY。\n"
                "请复制 .env.example 为 .env 并填入你的 API Key。"
            )

    @classmethod
    def print_config(cls) -> dict:
        """打印当前配置（脱敏）。"""
        key = cls.DEEPSEEK_API_KEY
        masked_key = key[:8] + "****" if len(key) > 8 else "****"
        return {
            "api_key": masked_key,
            "base_url": cls.DEEPSEEK_BASE_URL,
            "model": cls.DEEPSEEK_MODEL,
            "db_path": str(cls.DB_PATH),
        }
