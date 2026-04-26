#!/usr/bin/env python
"""Test script to verify LLM gateway is working correctly."""
import asyncio
import sys

from gateway.llm_gateway import LLMGateway, LLMMessage


async def test_llm_gateway():
    """Test the LLM gateway with a simple query."""
    print("Testing LLM Gateway...")
    print("=" * 60)

    gateway = LLMGateway()

    messages = [
        LLMMessage(role="system", content="You are a helpful assistant."),
        LLMMessage(role="user", content="Say 'Hello, World!' in exactly those words."),
    ]

    try:
        print("Sending request to LLM...")
        print(f"  Provider: {gateway.primary_provider.value}")

        # Check API key
        api_key = gateway.config.nvidia_nim_api_key.get_secret_value()
        print(f"  API Key length: {len(api_key)}")
        print(f"  API Key (first 10 chars): {api_key[:10] if len(api_key) > 10 else api_key}...")
        print(f"  Base URL: {gateway.config.nvidia_nim_base_url}")
        print(f"  Model: {gateway.config.nvidia_nim_model}")
        print()

        if not api_key:
            print("ERROR: API key is empty!")
            return False

        response = await gateway.complete(messages)

        print(f"Success!")
        print(f"  Provider: {response.provider.value}")
        print(f"  Model: {response.model}")
        print(f"  Tokens used: {response.tokens_used}")
        print(f"  Response: {response.content}")
        print()

        # Test streaming
        print("Testing streaming...")
        print("  Streaming response: ", end="", flush=True)

        async for chunk in gateway.complete_stream(messages):
            print(chunk, end="", flush=True)

        print()
        print("Streaming test complete!")
        print()

        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await gateway.close()


if __name__ == "__main__":
    success = asyncio.run(test_llm_gateway())
    sys.exit(0 if success else 1)
