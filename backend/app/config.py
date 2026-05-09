from pathlib import Path
from pydantic_settings import BaseSettings

# Look for .env in backend/ dir or project root, whichever exists
_here = Path(__file__).parent.parent  # backend/
_root = _here.parent                  # project root
_env_file = _here / ".env" if (_here / ".env").exists() else _root / ".env"


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/customer_research"
    REDIS_URL: str = "redis://localhost:6379"

    S3_BUCKET: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"

    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 500

    model_config = {"env_file": str(_env_file), "env_file_encoding": "utf-8"}


settings = Settings()
