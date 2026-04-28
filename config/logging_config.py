"""Logging configuration for OpenAGI v5.

Configures structlog with UTF-8 encoding to handle Unicode characters
on Windows and other platforms.
"""
import sys
from pathlib import Path

import structlog
from structlog.types import Processor

BASE_DIR = Path(__file__).parent.parent


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure structlog with UTF-8 encoding.

    This fixes Unicode encoding issues on Windows where the default
    console encoding (cp1252) cannot handle all Unicode characters.
    """
    # Set UTF-8 encoding for stdout/stderr
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            # Fallback for systems that don't support reconfigure
            pass

    if sys.stderr.encoding != "utf-8":
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            # Fallback for systems that don't support reconfigure
            pass

    # Configure structlog
    structlog.configure(
        processors=[
            # Add log level
            structlog.stdlib.add_log_level,
            # Add logger name
            structlog.stdlib.add_logger_name,
            # Add timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Format as JSON for machine readability
            structlog.processors.JSONRenderer()
        ],
        # Use standard library logging under the hood
        wrapper_class=structlog.stdlib.BoundLogger,
        # Context class
        context_class=dict,
        # Logger factory
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache logger on first use
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (optional)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# Auto-configure on import
configure_logging()
