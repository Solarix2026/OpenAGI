"""Pydantic settings for OpenAGI v5.

Loads from .env file or environment variables.
Never hardcoded - always configurable.
"""
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent


class TrustZones(BaseSettings):
    """Defines TRUSTED / SANDBOXED / ISOLATED execution contexts."""

    trusted: Path = Field(default=BASE_DIR / ".trust" / "trusted")
    sandboxed: Path = Field(default=BASE_DIR / ".trust" / "sandboxed")
    isolated: Path = Field(default=BASE_DIR / ".trust" / "isolated")


class MemorySettings(BaseSettings):
    """Memory layer configuration."""

    working_ttl: int = Field(default=3600, description="Working memory TTL in seconds")
    episodic_capacity: int = Field(default=10000, description="Max episodic memories")
    semantic_dim: int = Field(default=384, description="Embedding dimension for semantic memory")
    hdc_dim: int = Field(default=10000, description="HDC hypervector dimension")
    procedural_db_path: Path = Field(default=BASE_DIR / ".memory" / "procedural.db")


class Settings(BaseSettings):
    """Main settings class. All configuration lives here."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / "config" / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Core identity
    agent_name: str = Field(default="OpenAGI-v5")
    session_id_prefix: str = Field(default="ag")

    # LLM Gateway Configuration
    llm_provider: Literal["nvidia_nim", "groq", "openai", "ollama"] = Field(default="nvidia_nim")

    # NVIDIA NIM (Primary)
    nvidia_nim_api_key: SecretStr = Field(default=SecretStr(""))
    nvidia_nim_base_url: HttpUrl = Field(default=HttpUrl("https://integrate.api.nvidia.com"))
    nvidia_nim_model: str = Field(default="meta/llama-3.1-70b-instruct")
    nvidia_nim_temperature: float = Field(default=0.2)
    nvidia_nim_max_tokens: int = Field(default=4096)

    # Groq (Router/Fast)
    groq_api_key: SecretStr = Field(default=SecretStr(""))
    groq_model: str = Field(default="llama-3.1-8b-instant")
    groq_temperature: float = Field(default=0.1)
    groq_max_tokens: int = Field(default=1024)

    # OpenAI (Fallback)
    openai_api_key: SecretStr = Field(default=SecretStr(""))
    openai_model: str = Field(default="gpt-4o-mini")

    # Ollama (Local)
    ollama_base_url: HttpUrl = Field(default=HttpUrl("http://localhost:11434"))
    ollama_model: str = Field(default="llama3.1")

    # Gateway routing thresholds
    router_token_threshold: int = Field(default=4000, description="Above this, use NIM")
    router_complexity_keywords: list[str] = Field(default=[
        "plan", "design", "architect", "refactor", "repair", "analyze"
    ])

    # Execution
    max_code_repair_attempts: int = Field(default=5)
    repl_timeout: int = Field(default=30)

    # Trust Zones
    trust_zones: TrustZones = Field(default_factory=TrustZones)

    # Memory
    memory: MemorySettings = Field(default_factory=MemorySettings)

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    log_format: Literal["json", "text"] = Field(default="json")

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    ws_keepalive: int = Field(default=30)


def get_settings() -> Settings:
    """Factory function for settings."""
    return Settings()
