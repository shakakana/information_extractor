"""
Logging configuration using Loguru.
"""

import sys
from pathlib import Path

from loguru import logger

from src.core.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """Set up application logging with Loguru."""
   
    # Remove default handler
    logger.remove()
   
    # Console handler
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
              "<level>{level: <8}</level> | "
              "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
              "<level>{message}</level>",
        colorize=True,
    )
   
    # File handler
    log_path = Path("logs")
    log_path.mkdir(exist_ok=True)
   
    logger.add(
        log_path / settings.LOG_FILE,
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="1 day",
        retention="30 days",
        compression="zip",
    )
   
    # Set logging level for external libraries
    logger.add(
        sys.stdout,
        level="WARNING",
        filter=lambda record: record["name"].startswith(("uvicorn", "sqlalchemy")),
    )
   
    logger.info("Logging configured successfully")


def get_logger(name: str) -> logger:
    """Get logger instance for a specific module."""
    return logger.bind(name=name)
