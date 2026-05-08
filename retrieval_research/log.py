from __future__ import annotations

import logging
import sys
from typing import Optional

_LOG_NAME = "retrieval_research"


def get_logger(name: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(_LOG_NAME if name is None else f"{_LOG_NAME}.{name}")
    return logger


def setup_logging(level: int = logging.INFO, log_path: Optional[str] = None) -> None:
    logger = logging.getLogger(_LOG_NAME)
    logger.setLevel(level)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(level)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    if log_path:
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def silence_noisy_third_party() -> None:
    for name in ("httpx", "httpcore", "google_genai", "PIL", "pdf2image", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)
