"""
Application settings loaded from environment variables.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """All configuration for the YouTube RAG Chatbot."""

    # --- Groq LLM ---
    GROQ_API_KEY: str = "your_groq_api_key_here"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # --- Embeddings ---
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # --- ChromaDB ---
    CHROMA_DB_PATH: str = "./data/chroma_db"

    # --- Transcript Chunking ---
    CHUNK_SECONDS: int = 60

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
