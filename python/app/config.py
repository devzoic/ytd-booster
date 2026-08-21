"""
Application configuration settings.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

import sys

# Determine writeable data directory and .env location
custom_env_file = os.getenv("YT_ENV_FILE")
custom_data_dir = os.getenv("YT_DATA_DIR")

if custom_data_dir:
    BASE_DIR = Path(custom_data_dir)
elif getattr(sys, 'frozen', False):
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", str(Path.home()))
        BASE_DIR = Path(appdata) / "yt-booster-node"
    else:
        BASE_DIR = Path.home() / ".config" / "yt-booster-node"
else:
    BASE_DIR = Path(__file__).parent.parent  # python/

ROOT_DIR = BASE_DIR.parent if not getattr(sys, 'frozen', False) else BASE_DIR

# Ensure writeable base dir exists
try:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# Load .env candidates in priority order
env_candidates = []
if custom_env_file:
    env_candidates.append(Path(custom_env_file))

env_candidates.extend([
    BASE_DIR / ".env",
    Path(__file__).parent.parent / ".env" if not getattr(sys, 'frozen', False) else None,
    ROOT_DIR / ".env",
    Path.cwd() / ".env"
])

for env_p in env_candidates:
    if env_p and env_p.exists():
        load_dotenv(dotenv_path=env_p, override=True)


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
        env_file=[str(p) for p in env_candidates if p and p.exists()],
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure profiles directory exists
        self.PROFILES_DIR.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()

