"""
Application configuration settings.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

import sys

# Define base paths
if getattr(sys, 'frozen', False):
    EXE_DIR = Path(sys.executable).parent
    BASE_DIR = Path.cwd() if (Path.cwd() / ".env").exists() else EXE_DIR
    ROOT_DIR = BASE_DIR
else:
    BASE_DIR = Path(__file__).parent.parent  # python/
    ROOT_DIR = BASE_DIR.parent               # project root /

# Explicitly load .env files from python/.env and root .env
python_env_file = BASE_DIR / ".env"
root_env_file = ROOT_DIR / ".env"

if python_env_file.exists():
    load_dotenv(dotenv_path=python_env_file, override=True)

if root_env_file.exists():
    load_dotenv(dotenv_path=root_env_file, override=False)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Settings
    APP_NAME: str = "YT Booster"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8008
    
    # Ngrok Settings (Automatic Public Tunnel)
    NGROK_DOMAIN: str = ""
    NGROK_AUTHTOKEN: str = ""
    NGROK_URL: str = ""
    
    # SaaS Multi-Tenant Device Registration Key
    SAAS_DEVICE_KEY: str = ""
    
    # Laravel API Settings
    LARAVEL_API_URL: str = "http://youtube.test/api"
    LARAVEL_API_TOKEN: str = ""
    
    # Paths
    BASE_DIR: Path = BASE_DIR
    PROFILES_DIR: Path = BASE_DIR / "profiles_data"
    
    # Chrome Settings
    CHROME_HEADLESS: bool = False
    CHROME_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    model_config = SettingsConfigDict(
        env_file=[str(python_env_file), str(root_env_file)],
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure profiles directory exists
        self.PROFILES_DIR.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()

