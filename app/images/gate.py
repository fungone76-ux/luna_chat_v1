# file: app/images/gate.py

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.services.llm_client import LLMReply


TRIGGER_WORDS = {
    "immagine", "immagini", "foto", "fotografia",
    "picture", "image", "pic", "photo",
}


class ImageDecision(BaseModel):
    will_generate: bool
    reason: Literal["user_request", "auto_by_tags", "no_trigger"] = "no_trigger"


def _user_asks_for_image(text: str) -> bool:
    """
    Ritorna True se nel testo dell'utente compaiono parole tipo 'foto', 'immagine', ecc.
    """
    if not text:
        return False
    lower = text.lower()
    return any(word in lower for word in TRIGGER_WORDS)


def decide_image_request(user_text: str, reply: LLMReply) -> ImageDecision:
    """
    V1: regole semplici e trasparenti.
    - Se l'utente chiede esplicitamente una foto/immagine -> user_request
    - Altrimenti, se il modello ha sia tags_en che visual_en -> auto_by_tags
    - Altrimenti niente.
    """
    # 1) Richiesta esplicita dell'utente
    if _user_asks_for_image(user_text):
        return ImageDecision(will_generate=True, reason="user_request")

    # 2) Auto in base ai tag del modello
    has_tags = bool(reply.tags_en)
    has_visual = bool(reply.visual_en and reply.visual_en.strip())

    if has_tags and has_visual:
        return ImageDecision(will_generate=True, reason="auto_by_tags")

    # 3) Nessun trigger
    return ImageDecision(will_generate=False, reason="no_trigger")
