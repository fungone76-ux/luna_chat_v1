# file: app/core/settings.py

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional, List

from pydantic import BaseModel


class LLMConfig(BaseModel):
    base_url: str                      # es. "http://127.0.0.1:5005/v1"
    api_key: str = "EMPTY"             # se "EMPTY" -> niente Authorization
    model: str                         # es. "llama-3.1-8b-instruct-q6_k"
    max_tokens: int = 180
    temperature: float = 0.7
    top_p: float = 0.9
    timeout_s: int = 420


class SDConfig(BaseModel):
    enabled: bool = True
    autodetect: bool = False
    prefer_ports: Optional[List[int]] = None

    base_url: str = "http://127.0.0.1:7860"
    default_steps: int = 24
    sampler: str = "DPM++ 2M Karras"
    cfg_scale: float = 3.5

    width_single: int = 512
    height_single: int = 768
    width_multi: int = 1024
    height_multi: int = 768
    width: int = 768
    height: int = 768

    timeout_s: int = 420


class PathsConfig(BaseModel):
    storage_dir: Path
    images_dir: Path
    logs_dir: Path


class LoggingConfig(BaseModel):
    level: str = "INFO"


class AppConfig(BaseModel):
    default_character: str
    llm: LLMConfig
    sd: SDConfig
    paths: PathsConfig
    logging: LoggingConfig = LoggingConfig()


def _project_root() -> Path:
    """
    Restituisce la root del progetto (cartella dove sta main.py).
    """
    # app/core/settings.py -> app/core -> app -> root
    return Path(__file__).resolve().parents[2]


@lru_cache()
def load_app_config() -> AppConfig:
    """
    Carica config/app_config.json e crea le cartelle necessarie.
    """
    root = _project_root()
    config_path = root / "config" / "app_config.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Config non trovata: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    cfg = AppConfig.model_validate(data)

    # Normalizza i percorsi (li rende assoluti)
    storage_dir = (root / cfg.paths.storage_dir).resolve()
    images_dir = (root / cfg.paths.images_dir).resolve()
    logs_dir = (root / cfg.paths.logs_dir).resolve()

    storage_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    cfg.paths.storage_dir = storage_dir
    cfg.paths.images_dir = images_dir
    cfg.paths.logs_dir = logs_dir

    return cfg
