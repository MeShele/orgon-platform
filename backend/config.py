"""ORGON Configuration loader."""

import os
import secrets
from pathlib import Path
from functools import lru_cache

import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

CONFIG_PATH = Path(__file__).parent.parent / "config" / "orgon.yaml"


@lru_cache()
def load_config() -> dict:
    """Load ORGON configuration from YAML + env overrides."""
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    # Env overrides
    config["auth"]["token"] = os.getenv("ORGON_ADMIN_TOKEN", "")
    config["safina"]["ec_private_key"] = os.getenv("SAFINA_EC_PRIVATE_KEY", "")

    # Telegram overrides
    if "telegram" in config:
        config["telegram"]["bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN", "")
        config["telegram"]["chat_id"] = os.getenv("TELEGRAM_CHAT_ID", "")

    # Database overrides
    db_path = config["database"]["path"]
    if not os.path.isabs(db_path):
        config["database"]["path"] = str(
            Path(__file__).parent.parent / db_path
        )
    
    # PostgreSQL URL from env
    config["database"]["postgresql_url"] = os.getenv("DATABASE_URL", "")

    return config


def get_config() -> dict:
    return load_config()


class Settings:
    """Application settings with env-based config."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._config = load_config()
        
        # JWT Secret Key (critical - must be secure!)
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        if jwt_secret:
            self.SECRET_KEY = jwt_secret
        else:
            self.SECRET_KEY = self._generate_secret_key()
        
        self._initialized = True
        
        # Database
        self.DATABASE_URL = self._config["database"]["postgresql_url"]
        
        # CORS
        self.CORS_ORIGINS = os.getenv(
            "CORS_ORIGINS", 
            "http://localhost:3000,https://orgon.asystem.ai"
        ).split(",")
        
        # Admin token (legacy - will be deprecated after multi-user)
        self.ADMIN_TOKEN = self._config["auth"]["token"]
        
        # Safina keys
        self.SAFINA_EC_PRIVATE_KEY = self._config["safina"]["ec_private_key"]
        
        self._initialized = True
    
    @staticmethod
    def _generate_secret_key() -> str:
        """
        Generate a secure secret key if none provided.
        WARNING: This will change on restart! Set JWT_SECRET_KEY in .env for production!
        """
        key = secrets.token_urlsafe(32)
        print(f"⚠️  WARNING: Using auto-generated JWT_SECRET_KEY (will change on restart!)")
        print(f"⚠️  For production, set JWT_SECRET_KEY in .env: {key}")
        return key


# Global settings instance (singleton)
_settings_instance = None

def get_settings():
    """Get singleton settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance

# Backward compatibility
settings = get_settings()
