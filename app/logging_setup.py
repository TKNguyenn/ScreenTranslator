from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.config import AppConfig


def configure_logging(config: AppConfig) -> None:
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = config.logs_dir / "app.log"

    root = logging.getLogger()
    root.setLevel(getattr(logging, config.app.log_level.upper(), logging.INFO))
    root.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
