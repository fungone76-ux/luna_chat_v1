# file: app/core/logging_config.py

import logging
from logging.handlers import RotatingFileHandler

from .settings import load_app_config


def configure_logging() -> None:
    """
    Configura il logging per l'app:
    - console
    - file rotante in storage/logs/app.log
    """
    cfg = load_app_config()
    logs_dir = cfg.paths.logs_dir
    log_file = logs_dir / "app.log"

    # Formatter unico
    fmt = "[%(asctime)s] [%(levelname)s] (%(name)s) %(message)s"
    formatter = logging.Formatter(fmt)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, cfg.logging.level.upper(), logging.INFO))

    # Puliamo handler esistenti per evitare duplicati
    root_logger.handlers.clear()

    # Console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(root_logger.level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File rotante
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2_000_000,   # ~2MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(root_logger.level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logging.getLogger(__name__).info("Logging configurato. File log: %s", log_file)
