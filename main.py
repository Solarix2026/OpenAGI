"""OpenAGI v5 — Entry Point

Main entry point for starting the OpenAGI v5 agent system.
"""
import structlog
import uvicorn

from config.settings import get_settings

logger = structlog.get_logger()


def main():
    """Main entry point - start the API server."""
    config = get_settings()

    logger.info(
        "main.starting",
        agent_name=config.agent_name,
        host=config.api_host,
        port=config.api_port,
    )

    agent_name_str = str(config.agent_name)
    print(f"{'='*60}")
    print(f"  {agent_name_str:^56}  ")
    print(f"  Self-Repairing, Tool-Discovering Agent System           ")
    print(f"{'='*60}")
    print(f"  API Server: http://{config.api_host}:{config.api_port}")
    print(f"  WebSocket:  ws://{config.api_host}:{config.api_port}/ws")
    print(f"  Health:     http://{config.api_host}:{config.api_port}/health")
    print(f"")
    print(f"  Press Ctrl+C to stop")
    print(f"")

    # Import and create the app
    from api.server import create_app
    app = create_app(settings=config)

    uvicorn.run(
        app,
        host=config.api_host,
        port=config.api_port,
        log_level=config.log_level.lower(),
        reload=False,
    )


if __name__ == "__main__":
    main()
