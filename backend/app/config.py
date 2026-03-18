from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings

_env_file = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    database_url: str = ""  # postgresql://user:pass@host:5432/postgres
    embedding_model: str = "FremyCompany/BioLORD-2023"
    embedding_dim: int = 768
    cross_encoder_model: str = "ncbi/MedCPT-Cross-Encoder"
    rerank_top_n: int = 200  # how many RRF candidates to rerank
    enable_cross_encoder: bool = True  # disable if memory-constrained
    max_upload_size: int = 50 * 1024 * 1024  # 50MB
    max_files_per_session: int = 5
    default_match_limit: int = 200  # return top 200 matches
    port: int = 8020
    cors_origins: list[str] = ["http://localhost:5173"]  # Vite dev server

    model_config = {"env_file": str(_env_file), "env_file_encoding": "utf-8"}


settings = Settings()
