# file: app/services/llm_client.py
from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import requests

from app.core.settings import load_app_config


@dataclass
class LLMReply:
    """
    Risposta strutturata del LLM per Luna Chat v1.

    - reply_it: risposta di Luna in italiano (mostrata in chat)
    - tags_en: lista di tag inglesi per la scena (per Stable Diffusion)
    - visual_en: descrizione cinematografica in inglese della scena
    - follow_up_action: controllo opzionale (es. "request_image")
    - raw_text: contenuto grezzo restituito dal modello
    """

    reply_it: str
    tags_en: List[str] = field(default_factory=list)
    visual_en: str = ""
    follow_up_action: Optional[str] = None
    raw_text: Optional[str] = None


def _parse_structured_text(s: str) -> Optional[Dict[str, Any]]:
    """
    Parser per il formato a blocchi:

        reply_it: ...
        tags_en: ["tag1", "tag2", ...]
        visual_en: ...

    Ritorna un dict {reply_it, tags_en(list), visual_en} oppure None
    se non trova alcun pattern significativo.
    """
    if not s:
        return None

    txt = s.strip()

    # reply_it: da "reply_it:" fino a prima di "tags_en:" o "visual_en:" o fine stringa
    m_reply = re.search(
        r"reply_it\s*:\s*(.+?)(?=\n\s*tags_en\s*:|\n\s*visual_en\s*:|\Z)",
        txt,
        re.DOTALL | re.IGNORECASE,
    )
    reply_it = m_reply.group(1).strip() if m_reply else ""

    # tags_en: può essere lista JSON/Python o elenco separato da virgole
    m_tags = re.search(
        r"tags_en\s*:\s*(.+?)(?=\n\s*visual_en\s*:|\Z)",
        txt,
        re.DOTALL | re.IGNORECASE,
    )
    tags_raw = m_tags.group(1).strip() if m_tags else ""
    tags: List[str] = []

    if tags_raw:
        try:
            # se comincia con [, prova a interpretarlo come lista python/json
            if tags_raw.lstrip().startswith("["):
                parsed = ast.literal_eval(tags_raw)
                if isinstance(parsed, (list, tuple)):
                    tags = [str(x).strip() for x in parsed if str(x).strip()]
            else:
                # altrimenti spezza su virgole
                parts = [p.strip() for p in tags_raw.split(",")]
                tags = [p for p in parts if p]
        except Exception:
            # fallback super difensivo: split su virgole e newline
            parts = re.split(r"[,\\n]", tags_raw)
            tags = [p.strip() for p in parts if p.strip()]

    # visual_en: tutto quello che viene dopo "visual_en:"
    m_visual = re.search(
        r"visual_en\s*:\s*(.+)$",
        txt,
        re.DOTALL | re.IGNORECASE,
    )
    visual = m_visual.group(1).strip() if m_visual else ""

    if not reply_it and not tags and not visual:
        return None

    return {
        "reply_it": reply_it or txt,
        "tags_en": tags,
        "visual_en": visual,
    }


class LLMClient:
    """
    Client HTTP per un endpoint /v1/chat/completions compatibile OpenAI
    (es. vLLM, llama.cpp server, ecc.).
    """

    def __init__(self) -> None:
        self.log = logging.getLogger(self.__class__.__name__)

        cfg = load_app_config().llm
        base_url = cfg.base_url.rstrip("/")
        self.model = cfg.model
        self.temperature = cfg.temperature
        self.top_p = cfg.top_p
        self.max_tokens = cfg.max_tokens
        self.timeout_s = cfg.timeout_s
        self.api_key: Optional[str] = None if cfg.api_key == "EMPTY" else cfg.api_key

        # Costruzione endpoint
        if base_url.endswith("/v1"):
            self.endpoint = f"{base_url}/chat/completions"
        else:
            self.endpoint = f"{base_url}/v1/chat/completions"

        self.log.info(
            "LLMClient inizializzato: endpoint=%s, model=%s, max_tokens=%d, temp=%.2f, top_p=%.2f, timeout=%ds",
            self.endpoint,
            self.model,
            self.max_tokens,
            self.temperature,
            self.top_p,
            self.timeout_s,
        )

    # ------------------------------------------------------------------
    # Costruzione messaggi
    # ------------------------------------------------------------------
    def _build_messages(self, character: Any, history: Sequence[Any]) -> List[Dict[str, str]]:
        """
        Prepara il contesto per il LLM:

        - Primo system: persona del personaggio (Luna, Stella, ecc.)
        - Secondo system: istruzioni su reply_it/tags_en/visual_en
        - Poi la history (user/assistant) in ordine.
        """
        persona_prompt = getattr(character, "system_prompt", None)
        if not persona_prompt:
            # fallback minimale se manca il system_prompt
            persona_prompt = (
                "You are a fictional Italian woman chatting with the user. "
                "You answer in Italian with a warm, playful, sensual tone, "
                "and you never break character."
            )

        format_instructions = (
            "FORMAT RULES (VERY IMPORTANT):\n\n"
            "You must ALWAYS answer using EXACTLY this structure, in this order,\n"
            "with no extra text before or after, no code fences:\n\n"
            "reply_it: <short reply in Italian, in character>\n"
            "tags_en: [\"tag1\", \"tag2\", \"tag3\", ...]\n"
            "visual_en: <cinematic English description of the image scene>\n\n"
            "DETAILS:\n"
            "1) reply_it:\n"
            "- This is the ONLY part shown to the user.\n"
            "- Write in Italian, short and direct, as the character (for example Luna, 41 years old, etc.).\n"
            "- DO NOT mention JSON, tags_en, visual_en, Stable Diffusion, prompts, AI, models.\n"
            "- Just talk naturally to the user.\n\n"
            "2) tags_en:\n"
            "- A list of 8 to 12 short tags in English.\n"
            "- Each tag should be 1–3 words, no punctuation.\n"
            "- Use only concepts useful for a photorealistic NSFW image, grouped across:\n"
            "  composition, body_coverage, pose, body_focus, subjects, camera, lighting,\n"
            "  environment, wardrobe, mood.\n"
            "- Do NOT include tokens like 'score_9', 'masterpiece', 'NSFW', '1girl', '2girls'.\n"
            "- Tags MUST be coherent with the current chat context, based on both the user's\n"
            "  last message and your reply.\n\n"
            "3) visual_en:\n"
            "- A single English paragraph, 30–60 words.\n"
            "- No commands (do NOT say 'the image should show', 'we see', 'create an image of').\n"
            "- Describe the scene like a cinematic frame: who is there, what they are doing,\n"
            "  environment, lighting, mood.\n"
            "- It MUST match what is happening between you and the user right now. If the user\n"
            "  asks for a beach scene, the description clearly happens on a beach. If there are\n"
            "  two women, make it explicit that there are two women.\n"
        )

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": persona_prompt},
            {"role": "system", "content": format_instructions},
        ]

        for msg in history:
            role = getattr(msg, "role", "user")
            text = getattr(msg, "text", "")

            if role == "character":
                messages.append({"role": "assistant", "content": text})
            elif role == "system":
                messages.append({"role": "system", "content": text})
            else:
                # qualunque cosa non sia 'character' o 'system' la trattiamo come 'user'
                messages.append({"role": "user", "content": text})

        return messages

    # ------------------------------------------------------------------
    # Chiamata al modello
    # ------------------------------------------------------------------
    def generate_reply(
        self,
        user_text: str,
        character: Any,
        history: Sequence[Any],
    ) -> LLMReply:
        """
        Chiamata sincrona al modello:

        - Costruisce i messages
        - Chiama /chat/completions
        - Parla l'output con _parse_structured_text
        - Se qualcosa va storto, restituisce una risposta di fallback.
        """
        messages = self._build_messages(character=character, history=history)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.log.debug(
            "Chiamata LLM: endpoint=%s, model=%s, history_len=%d",
            self.endpoint,
            self.model,
            len(history),
        )

        raw_text: Optional[str] = None

        try:
            resp = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout_s,
            )
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
        except Exception as e:
            self.log.error("Errore chiamata LLM o formato risposta: %s", e)
            # fallback minimale
            return LLMReply(
                reply_it="[Scusa, ho avuto un problema tecnico con il modello. Riproviamo tra poco.]",
                tags_en=[],
                visual_en="",
                follow_up_action=None,
                raw_text=raw_text,
            )

        # Parsing del testo prodotto dal modello
        parsed = _parse_structured_text(raw_text or "")
        if not parsed:
            # il modello non ha rispettato il formato → risposta solo testuale
            self.log.warning(
                "Output LLM senza struttura attesa, uso fallback minimale. Contenuto grezzo: %r",
                raw_text,
            )
            return LLMReply(
                reply_it=(raw_text or "").strip(),
                tags_en=[],
                visual_en="",
                follow_up_action=None,
                raw_text=raw_text,
            )

        reply_it = str(parsed.get("reply_it") or "").strip()
        tags_en_raw = parsed.get("tags_en") or []
        visual_en = str(parsed.get("visual_en") or "").strip()

        if isinstance(tags_en_raw, list):
            tags_en = [str(t).strip() for t in tags_en_raw if str(t).strip()]
        else:
            tags_en = [str(tags_en_raw).strip()] if str(tags_en_raw).strip() else []

        # piccoli controlli e warning non bloccanti
        if tags_en:
            if not (8 <= len(tags_en) <= 12):
                self.log.warning(
                    "tags_en fuori range (8–12): count=%d, tags=%r",
                    len(tags_en),
                    tags_en,
                )

        if visual_en:
            wc = len(visual_en.split())
            if not (30 <= wc <= 60):
                self.log.warning(
                    "visual_en fuori range (30–60 parole): count=%d, visual_en=%r",
                    wc,
                    visual_en,
                )

        return LLMReply(
            reply_it=reply_it or (raw_text or "").strip(),
            tags_en=tags_en,
            visual_en=visual_en,
            follow_up_action=None,
            raw_text=raw_text,
        )
