from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # Database
    database_url: str = "postgresql+asyncpg://argent:changeme@localhost:5432/argent"

    # Redis
    redis_url: str = "redis://:changeme@localhost:6379/0"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_token: str = "changeme_chroma_token"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"

    # LiveKit
    livekit_url: str = "http://localhost:7880"
    livekit_ws_url: str = "ws://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "devsecret_must_be_at_least_32_chars_long"

    # Piper TTS
    piper_model_path: str = "/piper-models/en_US-lessac-medium.onnx"

    # Auth
    secret_key: str = "changeme_jwt_secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    staff_username: str = "admin"
    staff_password: str = "changeme"


@lru_cache
def get_settings() -> Settings:
    return Settings()
