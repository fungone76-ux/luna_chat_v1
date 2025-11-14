# file: main.py
from __future__ import annotations

import logging
import sys
from pathlib import Path
import faulthandler

from PySide6 import QtWidgets

from app.core.logging_config import configure_logging
from app.core.settings import load_app_config
from app.chat.engine import ChatEngine
from app.services.llm_client import LLMClient
from app.services.sd_client import SDClient
from app.images.engine import ImageEngine
from app.ui.main_window import MainWindow


def main() -> None:
    # Abilita faulthandler per debug crash strani
    faulthandler.enable(all_threads=True)

    # Logging
    configure_logging()
    log = logging.getLogger("main")

    # Config
    cfg = load_app_config()
    root_dir = Path(__file__).resolve().parent
    storage_dir = root_dir / "storage"
    images_dir = storage_dir / "images"
    logs_dir = storage_dir / "logs"

    # Assicura che le cartelle base esistano
    images_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    log.info("=== Avvio Luna Chat V1 (GUI) ===")
    log.info("Config caricata. Default character: %s", cfg.default_character)
    log.info("Percorsi:")
    log.info("  storage_dir = %s", storage_dir)
    log.info("  images_dir  = %s", images_dir)
    log.info("  logs_dir    = %s", logs_dir)

    # Servizi core
    llm_client = LLMClient()
    chat_engine = ChatEngine.from_defaults(llm_client)
    image_engine = ImageEngine.from_defaults()
    sd_client = SDClient()

    # Qt Application
    app = QtWidgets.QApplication(sys.argv)

    # Carica tema QSS se presente
    qss_path = root_dir / "ui" / "theme.qss"
    if qss_path.exists():
        try:
            with qss_path.open("r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
            log.info("Tema QSS caricato da %s", qss_path)
        except Exception as e:
            log.warning("Impossibile caricare theme.qss: %s", e)

    # Finestra principale
    win = MainWindow(chat_engine, image_engine, sd_client)
    win.show()

    # Event loop Qt
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


