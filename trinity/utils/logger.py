"""
Trinity Phase 2 - Logging Configuration
Centralized logging setup with file and console outputs
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logger(config: dict):
    """
    Setup application logging

    Args:
        config: Configuration dictionary
    """
    # Remove default handler
    logger.remove()

    # Get logging configuration
    log_config = config.get('logging', {})
    log_level = log_config.get('level', 'INFO')
    log_format = log_config.get('format',
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    # Console logging
    console_config = log_config.get('console', {})
    if console_config.get('enabled', True):
        logger.add(
            sys.stdout,
            format=log_format,
            level=log_level,
            colorize=console_config.get('colorize', True),
            backtrace=True,
            diagnose=True
        )

    # File logging
    file_config = log_config.get('file', {})
    if file_config.get('enabled', True):
        log_path = file_config.get('path', 'logs/trinity_{time:YYYY-MM-DD}.log')

        # Create logs directory
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_path,
            format=log_format,
            level=log_level,
            rotation=file_config.get('rotation', '1 day'),
            retention=file_config.get('retention', '30 days'),
            compression=file_config.get('compression', 'zip'),
            backtrace=True,
            diagnose=True
        )

    logger.info("Logger initialized")
    logger.info(f"Log level: {log_level}")


def get_logger(name: str = None):
    """
    Get logger instance

    Args:
        name: Logger name (optional)

    Returns:
        Logger instance
    """
    return logger.bind(name=name) if name else logger
