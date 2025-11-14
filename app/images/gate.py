# file: app/images/gate.py

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.services.llm_client import LLMReply

# Parole chiave nella richiesta dell'utente
USER_TRIGGER_WORDS = {
    "immagine", "immagini", "foto", "fotografia",
    "picture", "image", "pic", "photo", "scatta", "mostrami", "fammi vedere"
}

# Parole chiave nella risposta del personaggio (promessa)
CHARACTER_PROMISE_WORDS = {
    "te la mando", "te la invio", "ecco una foto", "te la mostro",
    "guarda questa", "ecco a te", "ecco per te", "ti invio"
}


class ImageDecision(BaseModel):
    will_generate: bool
    reason: Literal["user_request", "character_promise", "auto_by_tags", "no_trigger"] = "no_trigger"


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


def decide_image_request(user_text: str, reply: LLMReply) -> ImageDecision:
    """
    Logica di decisione per la generazione di immagini.
    L'immagine viene generata solo se ALMENO DUE delle seguenti condizioni sono vere:
    1. Richiesta esplicita dell'utente.
    2. Promessa esplicita del personaggio.
    3. Risposta del modello "molto visual" (visual_en + almeno 5 tags_en).
    """
    # Valutiamo le tre condizioni in modo indipendente
    is_user_request = _user_asks_for_image(user_text)
    is_character_promise = _character_promises_image(reply.reply_it)

    has_visual = bool(reply.visual_en and reply.visual_en.strip())
    sufficient_tags = len(reply.tags_en) >= 5 if reply.tags_en else False
    is_visual_reply = has_visual and sufficient_tags

    # Contiamo quante condizioni sono vere
    trigger_count = int(is_user_request) + int(is_character_promise) + int(is_visual_reply)

    # Se il punteggio è almeno 2, generiamo l'immagine
    if trigger_count >= 2:
        # Determiniamo la "ragione" con una priorità
        final_reason: Literal["user_request", "character_promise", "auto_by_tags"]
        if is_user_request:
            final_reason = "user_request"
        elif is_character_promise:
            final_reason = "character_promise"
        else:
            final_reason = "auto_by_tags"

        return ImageDecision(will_generate=True, reason=final_reason)

    # Altrimenti, nessuna generazione
    return ImageDecision(will_generate=False, reason="no_trigger")