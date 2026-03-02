from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = ""  # postgresql://user:pass@host:5432/postgres
    embedding_model: str = "all-MiniLM-L6-v2"
    max_upload_size: int = 50 * 1024 * 1024  # 50MB
    max_files_per_session: int = 5
    default_match_limit: int = 200  # return top 200 matches
    cors_origins: list[str] = ["http://localhost:5173"]  # Vite dev server

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
