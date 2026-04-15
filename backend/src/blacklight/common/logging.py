"""
Structured logging configuration using structlog.

This module provides centralized logging configuration with:
- Component-level log level control
- Structured logging (JSON for production, console for development)
- Request correlation ID tracking
- Environment and hostname context
- Sensitive data sanitization
- Log rotation and retention
- Integration with Python's standard logging
"""

import logging
import logging.handlers
import os
import socket
import sys
from pathlib import Path
from typing import Any

import structlog
from pythonjsonlogger import jsonlogger

from src.blacklight.common.settings import settings


def add_correlation_id(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    Add correlation ID to log entries.

    Retrieves correlation ID from asgi-correlation-id context and adds it to logs.
    """
    from asgi_correlation_id import correlation_id

    if request_id := correlation_id.get():
        event_dict["request_id"] = request_id
    return event_dict


def add_environment_context(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    Add environment context to all log entries.

    Includes:
    - environment: dev/staging/prod from settings
    - hostname: machine hostname for identifying instances
    - service: application name
    """
    event_dict["environment"] = settings.environment
    event_dict["hostname"] = socket.gethostname()
    event_dict["service"] = "blacklight"
    return event_dict


def add_user_context(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    Add user context to log entries from context vars.

    Retrieves user_id from context vars if available (set by middleware/dependencies).
    """
    try:
        from src.blacklight.common.audit import _user_context

        if user := _user_context.get(None):
            event_dict["user_id"] = user.id
    except (ImportError, AttributeError):
        # If user context is not available, skip
        pass
    return event_dict


def sanitize_sensitive_data(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    Sanitize sensitive data from log entries.

    Redacts:
    - OAuth codes and tokens
    - Passwords
    - API keys
    - Authorization headers
    - Email addresses (partial redaction)
    """
    sensitive_keys = {
        "code", "access_token", "refresh_token", "token",
        "password", "secret", "api_key", "authorization",
        "client_secret", "private_key"
    }

    def redact_value(key: str, value: Any) -> Any:
        """Redact sensitive values."""
        if isinstance(value, str):
            key_lower = key.lower()
            # Redact completely
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                return "***REDACTED***"
            # Partial email redaction
            if "email" in key_lower and "@" in value:
                parts = value.split("@")
                return f"{parts[0][:2]}***@{parts[1]}"
        elif isinstance(value, dict):
            return {k: redact_value(k, v) for k, v in value.items()}
        elif isinstance(value, list):
            return [redact_value(key, item) for item in value]
        return value

    # Sanitize all fields in event_dict
    for key in list(event_dict.keys()):
        if key not in ("timestamp", "level", "logger", "event"):
            event_dict[key] = redact_value(key, event_dict[key])

    return event_dict


def add_log_level_compact(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    Add log level to event dict without padding.

    This replaces structlog.stdlib.add_log_level to avoid padding.
    """
    event_dict["level"] = method_name
    return event_dict


class CompactConsoleRenderer:
    """
    Custom console renderer without log level padding.

    Based on structlog.dev.ConsoleRenderer but with compact formatting.
    """

    def __init__(self):
        """Initialize renderer with color codes."""
        self.level_colors = {
            "critical": "\x1b[31;1m",  # bright red
            "exception": "\x1b[31;1m",  # bright red
            "error": "\x1b[31m",  # red
            "warn": "\x1b[33m",  # yellow
            "warning": "\x1b[33m",  # yellow
            "info": "\x1b[32;1m",  # bright green
            "debug": "\x1b[36m",  # cyan
            "notset": "\x1b[37m",  # white
        }
        self.reset = "\x1b[0m"
        self.dim = "\x1b[2m"
        self.bright = "\x1b[1m"
        self.cyan = "\x1b[36m"
        self.magenta = "\x1b[35m"
        self.blue_bold = "\x1b[34;1m"

    def __call__(self, logger: Any, name: str, event_dict: dict) -> str:
        """Render a log entry."""
        # Extract components
        timestamp = event_dict.pop("timestamp", "")
        level = event_dict.pop("level", "info")
        logger_name = event_dict.pop("logger", "")
        event = event_dict.pop("event", "")

        # Get level color
        level_color = self.level_colors.get(level, self.reset)

        # Format output
        parts = []

        # Timestamp (dimmed)
        if timestamp:
            parts.append(f"{self.dim}{timestamp}{self.reset}")

        # Level (colored, no padding)
        parts.append(f"[{level_color}{self.bright}{level}{self.reset}]")

        # Event name (bright white)
        parts.append(f"{self.bright}{event}{self.reset}")

        # Logger name (blue bold)
        if logger_name:
            parts.append(f"[{self.blue_bold}{logger_name}{self.reset}]")

        # Join main parts
        output = " ".join(parts)

        # Add extra fields (key=value)
        if event_dict:
            extra_parts = []
            for key, value in sorted(event_dict.items()):
                if key == "exc_info":
                    continue  # Handle separately
                # Color keys cyan, values magenta
                extra_parts.append(f"{self.cyan}{key}{self.reset}={self.magenta}{value}{self.reset}")

            if extra_parts:
                output += " " + " ".join(extra_parts)

        return output


def configure_logging() -> None:
    """
    Configure application-wide structured logging.

    This function should be called once at application startup.
    It configures:
    - structlog processors and renderers
    - Python standard logging handlers
    - Component-level loggers
    - Log rotation
    """
    # Determine log level
    log_level = logging.getLevelName(settings.log_level.upper())

    # Configure Python's standard logging
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        handlers=[],  # We'll add handlers below
    )

    # Suppress uvicorn access logs (we'll log requests in middleware)
    logging.getLogger("uvicorn.access").disabled = True

    # Propagate uvicorn error logs through our logger
    logging.getLogger("uvicorn").handlers = []
    logging.getLogger("uvicorn").propagate = True

    # Create log directory if needed
    if settings.log_file_enabled:
        log_dir = Path(settings.log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

    # Configure handlers
    handlers: list[logging.Handler] = []

    # Console handler (always enabled)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    handlers.append(console_handler)

    # File handler with rotation
    if settings.log_file_enabled:
        if settings.log_rotation == "daily":
            # Daily rotation at midnight
            file_handler = logging.handlers.TimedRotatingFileHandler(
                filename=settings.log_file_path,
                when="midnight",
                interval=1,
                backupCount=settings.log_retention_days,
                encoding="utf-8",
            )
        else:
            # Size-based rotation
            max_bytes = settings.log_max_size_mb * 1024 * 1024
            file_handler = logging.handlers.RotatingFileHandler(
                filename=settings.log_file_path,
                maxBytes=max_bytes,
                backupCount=settings.log_retention_days,
                encoding="utf-8",
            )

        file_handler.setLevel(log_level)
        handlers.append(file_handler)

    # Add handlers to root logger
    root_logger = logging.getLogger()
    root_logger.handlers = handlers

    # Configure structlog processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        add_log_level_compact,  # Custom processor without padding
        add_environment_context,  # Add environment, hostname, service
        add_user_context,  # Add user_id from context vars
        add_correlation_id,  # Add request correlation ID
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        sanitize_sensitive_data,  # Sanitize before rendering (MUST be last processor before renderer)
    ]

    # Choose renderer based on environment
    if settings.log_format == "json":
        # JSON output for production
        renderer = structlog.processors.JSONRenderer()
        # Also configure JSON for file handler
        if settings.log_file_enabled and len(handlers) > 1:
            json_formatter = jsonlogger.JsonFormatter(  # type: ignore[attr-defined]
                "%(timestamp)s %(level)s %(name)s %(message)s"
            )
            handlers[1].setFormatter(json_formatter)
    else:
        # Pretty console output for development (compact, no padding)
        renderer = CompactConsoleRenderer()

    # Configure structlog
    structlog.configure(
        processors=shared_processors
        + [
            structlog.processors.UnicodeDecoder(),
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure component-level loggers
    configure_component_loggers()


def configure_component_loggers() -> None:
    """
    Configure individual logger levels for each feature component.
    """
    # Auth feature logger
    auth_logger = logging.getLogger("blacklight.auth")
    auth_logger.setLevel(
        logging.getLevelName(settings.effective_log_level_auth.upper())
    )

    # Agents feature logger
    agents_logger = logging.getLogger("blacklight.agents")
    agents_logger.setLevel(
        logging.getLevelName(settings.effective_log_level_agents.upper())
    )

    # Executions feature logger
    executions_logger = logging.getLogger("blacklight.executions")
    executions_logger.setLevel(
        logging.getLevelName(settings.effective_log_level_executions.upper())
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a configured structlog logger for a specific component.

    Args:
        name: Logger name (e.g., "blacklight.auth")

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)
