# file: app/core/models.py

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Literal

from pydantic import BaseModel, Field


# -------------------------
#  Modelli per i personaggi
# -------------------------


class CharacterSafety(BaseModel):
    nsfw_allowed: bool = False


class IpAdapterConfig(BaseModel):
    enabled: bool = False
    preprocessor: Optional[str] = None
    model: Optional[str] = None
    weight: float = 1.0
    guidance_start: float = 0.0
    guidance_end: float = 1.0
    processor_res: int = 1024
    resize_mode: Optional[str] = None
    image_path: Optional[str] = None


class MoodState(BaseModel):
    name: str
    affinity_threshold: float
    color: str
    description: str


class Character(BaseModel):
    """
    Rappresenta un personaggio così come definito in config/characters.json.
    I campi corrispondono al tuo JSON attuale.
    """

    name: str
    color: str
    avatar_path: Optional[str] = None
    system_prompt: str
    base_prompt: str
    negative_prompt: str
    tone: Optional[str] = None
    style_tags: List[str] = Field(default_factory=list)
    safety: CharacterSafety = Field(default_factory=CharacterSafety)
    ip_adapter: Optional[IpAdapterConfig] = None
    relationships: Dict[str, Dict[str, object]] = Field(default_factory=dict)
    mood_states: List[MoodState] = Field(default_factory=list)


def _project_root() -> Path:
    # app/core/models.py -> app/core -> app -> root
    return Path(__file__).resolve().parents[2]


def load_characters(config_path: Optional[Path] = None) -> Dict[str, Character]:
    """
    Carica config/characters.json e restituisce un dict {nome: Character}.
    Usa il file che hai messo in config/characters.json.
    """
    if config_path is None:
        config_path = _project_root() / "config" / "characters.json"

    if not config_path.exists():
        raise FileNotFoundError(f"characters.json non trovato: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    characters: Dict[str, Character] = {}
    for name, data in raw.items():
        # Aggiungiamo il nome come campo esplicito
        model_data = {"name": name, **data}
        characters[name] = Character.model_validate(model_data)

    return characters


# -------------------------
#  Modelli per la chat base
# -------------------------


class ChatMessage(BaseModel):
    role: Literal["user", "character", "system"]
    speaker: str
    text: str
    timestamp: float


class SessionState(BaseModel):
    """
    Stato minimale per V1 (solo 1-to-1).
    """
    session_id: str
    character_name: str
    history: List[ChatMessage] = Field(default_factory=list)

    @property
    def last_speaker(self) -> Optional[str]:
        return self.history[-1].speaker if self.history else None
