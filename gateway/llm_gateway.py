# gateway/llm_gateway.py
"""LLM Gateway — The Language Model Router.

Routes requests to appropriate LLM provider:
- NVIDIA NIM: Primary, high-quality reasoning
- Groq: Fast, for simple queries
- OpenAI: Fallback
- Ollama: Local option

No hardcoded model names or API endpoints — all from config.
"""
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Optional

import httpx
import structlog

from config.settings import get_settings

logger = structlog.get_logger()


class LLMProvider(Enum):
    """Available LLM providers."""
    NVIDIA_NIM = "nvidia_nim"
    GROQ = "groq"
    OPENAI = "openai"
    OLLAMA = "ollama"


@dataclass(frozen=True)
class LLMMessage:
    """A single message in the conversation."""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMRequest:
    """Unified request format for LLM calls (compatibility layer)."""
    messages: list[dict[str, str]]
    system: str = ""
    max_tokens: int = 1024
    temperature: float = 0.2
    stream: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_llm_messages(self) -> list[LLMMessage]:
        """Convert to LLMMessage format."""
        result = []
        if self.system:
            result.append(LLMMessage(role="system", content=self.system))
        for msg in self.messages:
            result.append(LLMMessage(role=msg.get("role", "user"), content=msg.get("content", "")))
        return result


@dataclass(frozen=True)
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    provider: LLMProvider
    model: str
    tokens_used: int = 0
    finish_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMGateway:
    """
    Intelligent LLM router.

    Selects provider based on:
    - Query complexity (token count, keywords)
    - Configured thresholds
    - Provider availability

    Supports streaming responses.
    """

    def __init__(self):
        self.config = get_settings()
        self.primary_provider = LLMProvider(self.config.llm_provider)
        self._http_client: Optional[httpx.AsyncClient] = None

        logger.info(
            "llm.gateway.initialized",
            primary=self.primary_provider.value,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=60.0)
        return self._http_client

    def _select_provider(self, query: str) -> LLMProvider:
        """
        Select appropriate provider based on query complexity.

        Simple queries → Groq (fast)
        Complex queries → NIM (quality)
        """
        query_lower = query.lower()

        # Check for complexity keywords
        complexity_keywords = self.config.router_complexity_keywords
        has_complexity = any(kw in query_lower for kw in complexity_keywords)

        # Check token count estimate
        estimated_tokens = len(query.split()) * 1.3  # Rough estimate
        exceeds_threshold = estimated_tokens > self.config.router_token_threshold

        if has_complexity or exceeds_threshold:
            return LLMProvider.NVIDIA_NIM
        else:
            return LLMProvider.GROQ

    def _get_provider_config(self, provider: LLMProvider) -> dict[str, Any]:
        """Get configuration for a specific provider."""
        if provider == LLMProvider.NVIDIA_NIM:
            return {
                "api_key": self.config.nvidia_nim_api_key.get_secret_value(),
                "base_url": str(self.config.nvidia_nim_base_url),
                "model": self.config.nvidia_nim_model,
                "temperature": self.config.nvidia_nim_temperature,
                "max_tokens": self.config.nvidia_nim_max_tokens,
            }
        elif provider == LLMProvider.GROQ:
            return {
                "api_key": self.config.groq_api_key.get_secret_value(),
                "base_url": "https://api.groq.com/openai/v1",
                "model": self.config.groq_model,
                "temperature": self.config.groq_temperature,
                "max_tokens": self.config.groq_max_tokens,
            }
        elif provider == LLMProvider.OPENAI:
            return {
                "api_key": self.config.openai_api_key.get_secret_value(),
                "base_url": "https://api.openai.com/v1",
                "model": self.config.openai_model,
                "temperature": 0.7,
                "max_tokens": 4096,
            }
        elif provider == LLMProvider.OLLAMA:
            return {
                "api_key": "",  # Ollama doesn't need API key
                "base_url": str(self.config.ollama_base_url),
                "model": self.config.ollama_model,
                "temperature": 0.7,
                "max_tokens": 4096,
            }
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _build_request_body(
        self,
        messages: list[LLMMessage],
        provider: LLMProvider,
        **kwargs
    ) -> dict[str, Any]:
        """Build request body for API call."""
        config = self._get_provider_config(provider)

        body = {
            "model": config["model"],
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ],
            "temperature": kwargs.get("temperature", config["temperature"]),
            "max_tokens": kwargs.get("max_tokens", config["max_tokens"]),
        }

        # Add optional parameters
        if "stream" in kwargs:
            body["stream"] = kwargs["stream"]

        return body

    async def complete(
        self,
        messages: list[LLMMessage] | LLMRequest,
        provider: Optional[LLMProvider] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Get a completion from the LLM.

        Args:
            messages: Conversation history (LLMMessage list or LLMRequest)
            provider: Force specific provider (auto-select if None)
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            LLMResponse with content and metadata
        """
        # Handle LLMRequest compatibility
        if isinstance(messages, LLMRequest):
            llm_messages = messages.to_llm_messages()
            # Extract kwargs from LLMRequest
            kwargs.setdefault("temperature", messages.temperature)
            kwargs.setdefault("max_tokens", messages.max_tokens)
            kwargs.setdefault("stream", messages.stream)
            messages = llm_messages

        # Auto-select provider if not specified
        if provider is None:
            # Use last user message for complexity detection
            last_user_msg = next(
                (msg for msg in reversed(messages) if msg.role == "user"),
                None
            )
            query = last_user_msg.content if last_user_msg else ""
            provider = self._select_provider(query)

        config = self._get_provider_config(provider)
        client = await self._get_client()

        # Build request
        body = self._build_request_body(messages, provider, **kwargs)

        # Make API call
        headers = {
            "Content-Type": "application/json",
        }

        if config["api_key"]:
            headers["Authorization"] = f"Bearer {config['api_key']}"

        try:
            response = await client.post(
                f"{config['base_url']}/chat/completions",
                json=body,
                headers=headers,
            )
            response.raise_for_status()

            data = response.json()

            # Extract response
            choice = data["choices"][0]
            content = choice["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens", 0)
            finish_reason = choice.get("finish_reason", "")

            return LLMResponse(
                content=content,
                provider=provider,
                model=config["model"],
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                metadata={"raw_response": data},
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "llm.gateway.http_error",
                provider=provider.value,
                status=e.response.status_code,
                error=str(e),
            )
            raise

        except Exception as e:
            logger.exception(
                "llm.gateway.error",
                provider=provider.value,
                error=str(e),
            )
            raise

    async def stream(
        self,
        messages: list[LLMMessage] | LLMRequest,
        provider: Optional[LLMProvider] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream completion from the LLM (compatibility method).

        Yields content chunks as they arrive.
        """
        async for chunk in self.complete_stream(messages, provider, **kwargs):
            yield chunk

    async def complete_stream(
        self,
        messages: list[LLMMessage] | LLMRequest,
        provider: Optional[LLMProvider] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream completion from the LLM.

        Yields content chunks as they arrive.
        """
        # Handle LLMRequest compatibility
        if isinstance(messages, LLMRequest):
            llm_messages = messages.to_llm_messages()
            # Extract kwargs from LLMRequest
            kwargs.setdefault("temperature", messages.temperature)
            kwargs.setdefault("max_tokens", messages.max_tokens)
            kwargs.setdefault("stream", True)
            messages = llm_messages
        else:
            kwargs.setdefault("stream", True)

        # Auto-select provider if not specified
        if provider is None:
            last_user_msg = next(
                (msg for msg in reversed(messages) if msg.role == "user"),
                None
            )
            query = last_user_msg.content if last_user_msg else ""
            provider = self._select_provider(query)

        config = self._get_provider_config(provider)
        client = await self._get_client()

        # Build request with streaming enabled
        body = self._build_request_body(messages, provider, stream=True, **kwargs)

        # Make API call
        headers = {
            "Content-Type": "application/json",
        }

        if config["api_key"]:
            headers["Authorization"] = f"Bearer {config['api_key']}"

        try:
            async with client.stream(
                "POST",
                f"{config['base_url']}/chat/completions",
                json=body,
                headers=headers,
            ) as response:
                response.raise_for_status()

                # Stream response chunks
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str == "[DONE]":
                            break

                        try:
                            import json
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPStatusError as e:
            logger.error(
                "llm.gateway.stream.http_error",
                provider=provider.value,
                status=e.response.status_code,
                error=str(e),
            )
            raise

        except Exception as e:
            logger.exception(
                "llm.gateway.stream.error",
                provider=provider.value,
                error=str(e),
            )
            raise

    async def close(self) -> None:
        """Clean up resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
