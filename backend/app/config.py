import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import MySQLDsn
from pathlib import Path

# backend/app/config.py lives 2 levels inside backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent  # = .../backend/
ROOT_DIR = BACKEND_DIR.parent                          # = .../transit-ai-system/
BASE_DIR = ROOT_DIR

# CatBoost model paths (constants, not configurable)
# Use absolute paths to avoid working directory issues
MODEL_PATH = str(Path(ROOT_DIR).absolute() / "outputs" / "models" / "catboost_demand_model.cbm")
MODEL_CONFIG_PATH = str(Path(ROOT_DIR).absolute() / "outputs" / "model_config.json")
TRAINING_METRICS_PATH = str(Path(ROOT_DIR).absolute() / "outputs" / "training_metrics.json")

# Print resolved paths for diagnostics
print(f"BASE_DIR: {BASE_DIR}")
print(f"MODEL_PATH: {MODEL_PATH}")
print(f"MODEL_CONFIG_PATH: {MODEL_CONFIG_PATH}")
print(f"TRAINING_METRICS_PATH: {TRAINING_METRICS_PATH}")
print(f"MODEL_PATH exists: {os.path.exists(MODEL_PATH)}")
print(f"MODEL_CONFIG_PATH exists: {os.path.exists(MODEL_CONFIG_PATH)}")
print(f"TRAINING_METRICS_PATH exists: {os.path.exists(TRAINING_METRICS_PATH)}")

class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "transit_ai"
    db_user: str = "root"
    db_password: str = "password"
    
    # CatBoost model paths (for backward compatibility)
    model_path: str = MODEL_PATH
    model_config_path: str = MODEL_CONFIG_PATH
    training_metrics_path: str = TRAINING_METRICS_PATH
    
    default_bus_capacity: int = 40
    database_type: str = "postgres"
    sqlite_database_url: str = f"sqlite:///{BACKEND_DIR / 'transit_ai.db'}"
    postgres_database_url: str = "postgresql://root:password@localhost:3306/transit_ai"
    
    # Groq API configuration (read from .env file)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_api_url: str = "https://api.groq.com/openai/v1/chat/completions"

    model_config = SettingsConfigDict(
        protected_namespaces=('settings_',),
        extra='ignore',
        # Load backend/.env first (most specific), then root .env as fallback.
        # Using absolute paths ensures correct resolution regardless of cwd.
        env_file=[
            str(ROOT_DIR / ".env"),
            str(BACKEND_DIR / ".env"),
        ],
        env_file_encoding="utf-8"
    )

    @property
    def database_url(self) -> str:
        if self.database_type.lower() == "sqlite":
            return self.sqlite_database_url
        from urllib.parse import quote_plus
        # Using self.postgres_database_url directly as originally intended when password is fully encoded,
        # but preserving original logic structure if needed.
        return self.postgres_database_url

settings = Settings()
