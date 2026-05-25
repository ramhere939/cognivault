"""
Application configuration via Pydantic BaseSettings.
All values loaded from .env file or environment variables.
"""
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # API Keys
    gemini_api_key: str
    groq_api_key: str
    groq_model: str = "openai/gpt-oss-120b"

    # Storage paths
    sqlite_path: str = "./data/sqlite/knowledge.db"
    chroma_path: str = "./data/chroma"
    graphs_path: str = "./data/graphs"
    uploads_path: str = "./data/uploads"

    # Gemini models (google-genai SDK — gemini-3.5-flash is GA)
    gemini_flash_model: str = "gemini-2.5-flash"
    gemini_pro_model: str = "gemini-2.5-flash"  # 2.5-flash replaces pro for most tasks
    gemini_embedding_model: str = "gemini-embedding-2"

    # Pipeline tuning
    chunk_size_tokens: int = 400
    chunk_overlap_tokens: int = 50
    max_retrieval_chunks: int = 10
    rerank_top_k: int = 5
    relationship_similarity_threshold: float = 0.72

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    def ensure_dirs(self):
        """Create all required data directories on startup."""
        for path_str in [self.sqlite_path, self.chroma_path, self.graphs_path, self.uploads_path]:
            path = Path(path_str)
            if path.suffix:  # it's a file path
                path.parent.mkdir(parents=True, exist_ok=True)
            else:
                path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
