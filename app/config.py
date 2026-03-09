"""
Application Configuration
Handles environment-specific settings
"""

import os


class Config:
    """Base configuration"""

    # ================= SECURITY =================
    SECRET_KEY = os.getenv("SECRET_KEY", "quizx_secret_key_change_in_production")

    # ================= AI / LLM =================
    # No dangerous default model here
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Use SAFE FREE MODEL as default
    AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "openrouter/free")

    # ================= GOOGLE OAUTH =================
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

    # ================= DATABASE =================
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:12345678@localhost:5432/quizx"
    )

    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.getenv("DB_POOL_SIZE", 10)),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", 20)),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", 1800)),
        "pool_pre_ping": True,
    }

    # ================= SESSION =================
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"

    # ================= APP =================
    TIMEZONE = "Asia/Kolkata"


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config():
    env = os.getenv("FLASK_ENV", "development").lower()
    return config.get(env, config["default"])