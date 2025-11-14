# file: app/images/gate.py

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.services.llm_client import LLMReply

# Parole chiave nella richiesta dell'utente
USER_TRIGGER_WORDS = {
    "immagine",
    "immagini",
    "foto",
    "fotografia",
    "picture",
    "image",
    "pic",
    "photo",
    "scatta",
    "mostrami",
    "fammi vedere",
    "mandami",
    "mandane",
}

# Parole chiave nella risposta del personaggio (promessa)
CHARACTER_PROMISE_WORDS = {
    "te la mando",
    "te la invio",
    "ti mando una foto",
    "ti mando la foto",
    "ecco una foto",
    "te la mostro",
    "guarda questa",
    "ecco a te",
    "ecco per te",
    "ti invio",
}


class ImageDecision(BaseModel):
    will_generate: bool
    reason: Literal[
        "user_request", "character_promise", "follow_up_action", "no_trigger"
    ] = "no_trigger"


def _user_asks_for_image(text: str) -> bool:
    """
    Ritorna True se nel testo dell'utente compaiono parole di richiesta immagine.
    """
    if not text:
        return False
    lower = text.lower()
    return any(word in lower for word in USER_TRIGGER_WORDS)


def _character_promises_image(text: str) -> bool:
    """
    Ritorna True se nella risposta del personaggio compaiono frasi di promessa.
    """
    if not text:
        return False
    lower = text.lower()
    return any(phrase in lower for phrase in CHARACTER_PROMISE_WORDS)


def _followup_requests_image(reply: LLMReply) -> bool:
    """
    True se il modello chiede esplicitamente di generare un'immagine via follow_up_action.
    """
    if not reply.follow_up_action:
        return False
    return reply.follow_up_action.strip().lower() == "request_image"


def decide_image_request(user_text: str, reply: LLMReply) -> ImageDecision:
    """
    Logica di decisione per la generazione di immagini.

    V1 (stretta, per evitare spam immagini):
    - Generiamo l'immagine SOLO se almeno UNA di queste è vera:
      1) Richiesta esplicita dell'utente (parole chiave).
      2) Promessa esplicita del personaggio (frasi tipo "te la mando una foto").
      3) follow_up_action == \"request_image\" nel JSON del LLM.

    Nessuna generazione automatica solo perché ci sono tags_en/visual_en.
    """
    is_user_request = _user_asks_for_image(user_text)
    is_character_promise = _character_promises_image(reply.reply_it)
    is_followup_request = _followup_requests_image(reply)

    if is_user_request:
        return ImageDecision(will_generate=True, reason="user_request")

    if is_character_promise:
        return ImageDecision(will_generate=True, reason="character_promise")

    if is_followup_request:
        return ImageDecision(will_generate=True, reason="follow_up_action")

    # Nessun trigger attivo → niente immagine
    return ImageDecision(will_generate=False, reason="no_trigger")
