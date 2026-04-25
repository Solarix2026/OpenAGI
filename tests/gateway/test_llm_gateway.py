# tests/gateway/test_llm_gateway.py
import pytest
from gateway.llm_gateway import LLMGateway, LLMProvider, LLMMessage, LLMResponse


def test_gateway_initialization():
    """Gateway initializes with config."""
    gateway = LLMGateway()

    assert gateway is not None
    assert gateway.primary_provider == LLMProvider.NVIDIA_NIM


def test_message_creation():
    """LLMMessage captures role and content."""
    msg = LLMMessage(role="user", content="Hello")

    assert msg.role == "user"
    assert msg.content == "Hello"


def test_response_creation():
    """LLMResponse captures completion data."""
    response = LLMResponse(
        content="Response text",
        provider=LLMProvider.NVIDIA_NIM,
        model="test-model",
        tokens_used=100,
    )

    assert response.content == "Response text"
    assert response.provider == LLMProvider.NVIDIA_NIM
    assert response.tokens_used == 100


def test_provider_enum_values():
    """Provider enum has correct values."""
    assert LLMProvider.NVIDIA_NIM.value == "nvidia_nim"
    assert LLMProvider.GROQ.value == "groq"
    assert LLMProvider.OPENAI.value == "openai"
    assert LLMProvider.OLLAMA.value == "ollama"


def test_gateway_selects_provider_by_complexity():
    """Gateway routes to appropriate provider based on complexity."""
    gateway = LLMGateway()

    # Simple query should use Groq (fast)
    simple_provider = gateway._select_provider("What is 2+2?")
    assert simple_provider in [LLMProvider.GROQ, LLMProvider.NVIDIA_NIM]

    # Complex query should use NIM (primary)
    complex_provider = gateway._select_provider("Design a complete system architecture for a distributed database")
    assert complex_provider == LLMProvider.NVIDIA_NIM


def test_gateway_builds_request_body():
    """Gateway builds correct request body for API calls."""
    gateway = LLMGateway()

    messages = [
        LLMMessage(role="system", content="You are helpful"),
        LLMMessage(role="user", content="Hello"),
    ]

    body = gateway._build_request_body(messages, LLMProvider.NVIDIA_NIM)

    assert "messages" in body
    assert len(body["messages"]) == 2
    assert "model" in body
    assert "temperature" in body
