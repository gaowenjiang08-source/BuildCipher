"""Logging utilities for BuildTrust Studio."""

import logging
import sys
from typing import Optional
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for terminal output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str = "cipher_genius",
    level: str = "INFO",
    log_file: Optional[Path] = None,
    use_colors: bool = True
) -> logging.Logger:
    """
    Setup a logger with console and optional file output.

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging
        use_colors: Whether to use colored output in console

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Set level
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # Format: [2025-10-18 10:30:45] INFO: Message
    if use_colors:
        console_formatter = ColoredFormatter(
            fmt='[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_formatter = logging.Formatter(
            fmt='[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        file_formatter = logging.Formatter(
            fmt='[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "cipher_genius") -> logging.Logger:
    """
    Get or create a logger instance.

    Args:
        name: Logger name (default: "cipher_genius")

    Returns:
        Logger instance
    """
    # Get the root cipher_genius logger
    root_name = name.split('.')[0] if '.' in name else name
    root_logger = logging.getLogger(root_name)

    # If root logger not configured, set up with defaults
    if not root_logger.handlers:
        setup_logger(root_name, level="INFO")  # Default to INFO level

    # Return the specific logger (will inherit from root)
    return logging.getLogger(name)


# Convenience function for setting log level
def set_log_level(level: str):
    """Set the global log level for all BuildTrust loggers."""
    logger = get_logger()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    for handler in logger.handlers:
        handler.setLevel(logging.DEBUG)
