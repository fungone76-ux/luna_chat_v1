# file: app/chat/engine.py

from __future__ import annotations

import logging
import time
from typing import Dict, Tuple

from app.core.models import Character, ChatMessage, SessionState, load_characters
from app.core.settings import load_app_config
from app.services.llm_client import LLMClient, LLMReply


class ChatEngine:
    """
    Motore di chat V1:
    - solo 1-to-1
    - usa il tuo LLM reale (LLMClient)
    - per ora non genera ancora immagini (ma otteniamo già tags_en / visual_en)
    """

    def __init__(
        self,
        characters: Dict[str, Character],
        default_character_name: str,
        llm_client: LLMClient,
    ) -> None:
        self.log = logging.getLogger(self.__class__.__name__)
        self.characters = characters
        self.default_character_name = default_character_name
        self.llm = llm_client

        if default_character_name not in characters:
            raise ValueError(
                f"Default character '{default_character_name}' non trovato in characters.json"
            )

    @classmethod
    def from_defaults(cls, llm_client: LLMClient) -> "ChatEngine":
        """
        Costruisce il ChatEngine usando config/app_config.json e characters.json.
        """
        cfg = load_app_config()
        characters = load_characters()
        return cls(
            characters=characters,
            default_character_name=cfg.default_character,
            llm_client=llm_client,
        )

    def start_session(self, session_id: str) -> SessionState:
        """
        Crea una nuova sessione 1-to-1 con il personaggio di default.
        """
        state = SessionState(
            session_id=session_id,
            character_name=self.default_character_name,
            history=[],
        )
        self.log.info(
            "Nuova sessione %s con personaggio %s",
            session_id,
            state.character_name,
        )
        return state

    def process_user_message(
        self,
        session: SessionState,
        user_text: str,
    ) -> Tuple[SessionState, LLMReply]:
        """
        Aggiunge il messaggio utente alla history, chiama l'LLM e aggiunge la risposta.
        Torna (nuovo_session_state, llm_reply).
        """
        now = time.time()

        # 1) Messaggio utente
        user_msg = ChatMessage(
            role="user",
            speaker="Tu",
            text=user_text,
            timestamp=now,
        )
        session.history.append(user_msg)

        character = self.characters[session.character_name]

        # 2) Chiamata LLM (reale, tramite LLMClient)
        reply = self.llm.generate_reply(
            user_text=user_text,
            character=character,
            history=session.history,
        )

        # 3) Messaggio del personaggio
        char_msg = ChatMessage(
            role="character",
            speaker=character.name,
            text=reply.reply_it,
            timestamp=time.time(),
        )
        session.history.append(char_msg)

        self.log.debug(
            "Session %s — user said %r, %s replied.",
            session.session_id,
            user_text,
            character.name,
        )

        return session, reply
