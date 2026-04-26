import os
import pytest
from pydantic_settings import SettingsConfigDict


def test_settings_loads_from_env():
    """Test that settings can load from environment variables."""
    os.environ["OPENAGI_LLM_PROVIDER"] = "nvidia_nim"
    os.environ["NVIDIA_NIM_API_KEY"] = "test-key"
    os.environ["NVIDIA_NIM_BASE_URL"] = "https://test.api.nvidia.com"
    os.environ["GROQ_API_KEY"] = "test-groq-key"

    from config.settings import Settings
    settings = Settings()

    assert settings.llm_provider == "nvidia_nim"
    assert settings.nvidia_nim_api_key.get_secret_value() == "test-key"
    assert str(settings.nvidia_nim_base_url) == "https://test.api.nvidia.com/"
    assert settings.groq_api_key.get_secret_value() == "test-groq-key"


def test_trust_zones_defined():
    """Test that trust zone paths are configured."""
    from config.settings import Settings, TrustZones
    settings = Settings()

    assert isinstance(settings.trust_zones, TrustZones)
    assert settings.trust_zones.trusted is not None
    assert settings.trust_zones.sandboxed is not None
    assert settings.trust_zones.isolated is not None


def test_memory_layers_configured():
    """Test memory layer settings."""
    from config.settings import Settings
    settings = Settings()

    assert settings.memory.working_ttl > 0
    assert settings.memory.episodic_capacity > 0
    assert settings.memory.semantic_dim > 0
    assert settings.memory.procedural_db_path is not None
