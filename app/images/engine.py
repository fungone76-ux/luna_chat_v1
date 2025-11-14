# file: app/images/engine.py

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from pydantic import BaseModel

from app.core.models import Character, load_characters
from app.core.settings import load_app_config
from app.services.llm_client import LLMReply

# Proviamo a importare l'adapter LoRA. Se non c'è, semplicemente non useremo LoRA.
try:
    from lora_mapping import collect_lora_tokens_from_config  # type: ignore
except ImportError:  # pragma: no cover - ambiente senza file
    collect_lora_tokens_from_config = None  # type: ignore


# Quality chain in stile tuo progetto
QUALITY_TAGS = [
    "score_9",
    "score_8_up",
    "score_7_up",
    "score_6_up",
    "score_5_up",
    "score_4_up",
    "masterpiece",
    "photorealistic",
    "award-winning photo",
]

QUALITY_CHAIN = ", ".join(QUALITY_TAGS)


class ImagePrompts(BaseModel):
    positive: str
    negative: str


class ImageEngine:
    """
    Costruisce i prompt SD a partire da:
    - base_prompt / negative_prompt del personaggio
    - tags_en / visual_en del LLM
    - (opzionale) LoRA tokens dal tuo lora_mapping.py

    V1: nessuna chiamata a SD, solo costruzione stringhe.
    """

    def __init__(self, characters: Dict[str, Character]) -> None:
        self.log = logging.getLogger(self.__class__.__name__)
        self.characters = characters
        self.app_cfg = load_app_config()

        try:
            # Dizionario grezzo per lora_mapping
            self._raw_cfg_dict = self.app_cfg.model_dump()
        except Exception:
            self._raw_cfg_dict = {}

    @classmethod
    def from_defaults(cls) -> "ImageEngine":
        chars = load_characters()
        return cls(chars)

    # -------------------------
    #  Helpers interni
    # -------------------------

    def _strip_quality_from_base(self, base: str) -> str:
        """
        Rimuove i tag di quality dal base_prompt per evitare duplicati,
        lasciando il resto invariato.
        """
        if not base:
            return ""
        text = base
        for qt in QUALITY_TAGS:
            text = text.replace(qt + ",", "")
            text = text.replace("," + qt, "")
            text = text.replace(qt, "")
        # pulizia rozza di spazi e virgole doppie
        while ", ," in text:
            text = text.replace(", ,", ",")
        return " ".join(text.replace(" ,", ",").split())

    def _normalize_tags(self, tags: List[str]) -> List[str]:
        """
        - trim degli spazi
        - rimozione duplicati (case-insensitive)
        """
        out: List[str] = []
        seen = set()
        for t in tags:
            if not t:
                continue
            clean = t.strip()
            if not clean:
                continue
            key = clean.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(clean)
        return out

    def _collect_lora_tokens(
        self,
        character: Character,
        tags_en: List[str],
        visual_en: str,
    ) -> List[str]:
        """
        Chiede al tuo lora_mapping i token <lora:NAME:WEIGHT>.
        Se qualcosa va storto, restituisce lista vuota senza fallback creativo.
        """
        if collect_lora_tokens_from_config is None:
            return []

        try:
            cfg = dict(self._raw_cfg_dict) if isinstance(self._raw_cfg_dict, dict) else {}
            subjects = [character.name]
            char_data = character.model_dump()
            tokens = collect_lora_tokens_from_config(
                cfg,
                mode="chat_1to1",
                subjects=subjects,
                character_data=char_data,
                tags_en=tags_en,
                visual_en=visual_en,
            )
            if not isinstance(tokens, list):
                return []
            return [str(t) for t in tokens if str(t).strip()]
        except Exception as e:
            self.log.error("Errore in collect_lora_tokens_from_config: %s", e)
            return []

    # -------------------------
    #  API principale
    # -------------------------

    def build_prompts(
        self,
        character_name: str,
        reply: LLMReply,
    ) -> ImagePrompts:
        """
        Costruisce (positive, negative) per un singolo personaggio.
        Non chiama ancora SD.
        """
        if character_name not in self.characters:
            raise ValueError(f"Personaggio sconosciuto: {character_name}")

        char = self.characters[character_name]

        base_clean = self._strip_quality_from_base(char.base_prompt)
        tags = self._normalize_tags(reply.tags_en)
        visual = (reply.visual_en or "").strip()

        # LoRA tokens (può essere vuota)
        lora_tokens = self._collect_lora_tokens(char, tags, visual)

        positive_parts: List[str] = []

        if QUALITY_CHAIN:
            positive_parts.append(QUALITY_CHAIN)
        if base_clean:
            positive_parts.append(base_clean)
        if tags:
            positive_parts.extend(tags)
        if visual:
            positive_parts.append(visual)
        if lora_tokens:
            positive_parts.extend(lora_tokens)

        positive = ", ".join(p for p in positive_parts if p)

        negative = (char.negative_prompt or "").strip()

        self.log.debug(
            "Prompts generati per %s: len(positive)=%d, len(negative)=%d",
            character_name,
            len(positive),
            len(negative),
        )

        return ImagePrompts(positive=positive, negative=negative)
