# file: app/services/llm_client.py

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Sequence, Optional

import requests
from pydantic import BaseModel, Field

from app.core.models import Character, ChatMessage
from app.core.settings import load_app_config


class LLMReply(BaseModel):
    reply_it: str
    tags_en: List[str] = Field(default_factory=list)
    visual_en: str = ""
    follow_up_action: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None


class LLMClient:
    def __init__(self) -> None:
        self.log = logging.getLogger(self.__class__.__name__)
        cfg = load_app_config().llm
        self.base_url = cfg.base_url.rstrip("/")
        self.model = cfg.model
        self.temperature = cfg.temperature
        self.top_p = cfg.top_p
        self.max_tokens = cfg.max_tokens
        self.timeout_s = cfg.timeout_s
        self.api_key: Optional[str] = None if cfg.api_key == "EMPTY" else cfg.api_key
        if self.base_url.endswith("/v1"):
            self.endpoint = f"{self.base_url}/chat/completions"
        else:
            self.endpoint = f"{self.base_url}/v1/chat/completions"
        self.log.info(
            "LLMClient inizializzato: endpoint=%s, model=%s, max_tokens=%d, temp=%.2f, top_p=%.2f, timeout=%ds",
            self.endpoint,
            self.model,
            self.max_tokens,
            self.temperature,
            self.top_p,
            self.timeout_s,
        )

    def _build_messages(
        self,
        character: Character,
        history: Sequence[ChatMessage],
    ) -> List[Dict[str, str]]:
        json_instructions = (
            "IMPORTANT JSON + TAGS + VISUAL RULES:\n\n"
            "You are ALSO an expert cinematic image director and SDXL-like image prompt designer,\n"
            "working strictly BEHIND the scenes for the character. You NEVER break character in the\n"
            "dialogue itself, but you carefully craft tags_en and visual_en as if you were designing\n"
            "a professional photorealistic NSFW image prompt.\n\n"
            "Your tags_en and visual_en MUST always be coherent with the CURRENT chat context.\n"
            "Always base them on BOTH: (1) the user's last message AND (2) what is happening between\n"
            "you (the character) and the user in this moment. Think of tags_en and visual_en as the\n"
            "visual translation of the current interaction, not a separate, random fantasy.\n\n"
            "You MUST respond in PURE JSON, with no extra text, no explanations, and no code fences.\n"
            "The JSON object must have exactly these keys:\n\n"
            "{\n"
            '  \"reply_it\": string,\n'
            '  \"tags_en\": string[],\n'
            '  \"visual_en\": string,\n'
            '  \"follow_up_action\": string | null\n'
            "}\n\n"
            "RULES:\n\n"
            "1) reply_it\n"
            "- Short reply in ITALIAN only.\n"
            "- Stay fully in character (Luna / the current character) in tone and personality.\n"
            "- Do NOT include any tags or technical notes here, just natural dialogue.\n"
            "- NEVER mention JSON, keys, tags_en, visual_en, Stable Diffusion, prompts, models,\n"
            "  being an AI, or any behind-the-scenes technical process in reply_it.\n"
            "- In reply_it you are just chatting like a real person in Italian.\n\n"
            "2) tags_en\n"
            "- An array of 8 to 12 short tags in English.\n"
            "- Each tag must be 1–3 words, no full sentences.\n"
            "- No punctuation inside a tag (no commas, no periods).\n"
            "- Tags must be meaningful for photorealistic image generation, not random adjectives.\n\n"
            "- The set of tags should jointly cover these conceptual families:\n"
            "  - composition (e.g. \"close-up\", \"three-quarter view\")\n"
            "  - body_coverage (e.g. \"full body\", \"half-length\")\n"
            "  - pose (e.g. \"leaning forward\", \"lying on bed\", \"lying on towel\")\n"
            "  - body_focus (e.g. \"intense gaze\", \"long legs\")\n"
            "  - subjects (e.g. \"woman\", \"two women\", \"mature woman\")\n"
            "  - camera (e.g. \"cinematic angle\", \"eye-level shot\")\n"
            "  - lighting (e.g. \"soft lighting\", \"moody lighting\", \"sunset lighting\")\n"
            "  - environment (e.g. \"bedroom\", \"red velvet curtain\", \"sandy beach\")\n"
            "  - wardrobe (e.g. \"silk robe\", \"lingerie\", \"bikini\", \"tight dress\")\n"
            "  - mood (e.g. \"sensual\", \"teasing\", \"intimate\")\n\n"
            "- Do NOT repeat the same concept twice.\n"
            "- Use only English words.\n"
            "- Do NOT include literal quality tokens like \"score_9\", \"masterpiece\", \"NSFW\" in tags_en.\n\n"
            "3) visual_en\n"
            "- A cinematic, descriptive English sentence or short paragraph.\n"
            "- Minimum 24 words, maximum 70 words.\n"
            "- No commands (do NOT say \"the image should show...\", \"we see...\", \"create an image of...\").\n"
            "- Do NOT include literal tags or technical tokens like \"score_9\", \"masterpiece\", \"NSFW\",\n"
            "  \"1girl\", \"2girls\", etc.\n"
            "- Clearly describe:\n"
            "  - who is in the scene (number and type of subjects),\n"
            "  - what they are doing (pose, gesture),\n"
            "  - the environment (bedroom, sofa, lights, beach, shower, etc.),\n"
            "  - the mood (sensual, playful, intimate, etc.).\n"
            "- The scene MUST look like a cinematic frame of what is happening between you and the user\n"
            "  right now, according to the last user message and your reply.\n"
            "- If the user asks for a beach scene, the visual_en MUST clearly describe a scene on the beach.\n"
            "- If there are two women in the scene, the description MUST make it clear that there are two women,\n"
            "  not \"a woman\".\n\n"
            "4) follow_up_action\n"
            "- Can be null or a short control string like \"request_image\".\n"
            "- Keep it null unless there is a clear need for a follow-up control action.\n\n"
            "Output ONLY the JSON object described above. Nothing before or after it."
        )
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": character.system_prompt},
            {"role": "system", "content": json_instructions},
        ]
        for msg in history:
            role = "user"
            if msg.role == "character":
                role = "assistant"
            elif msg.role == "system":
                role = "system"
            messages.append({"role": role, "content": msg.text})
        return messages

    def _parse_llm_content(self, content: str) -> Dict[str, Any]:
        """
        Tenta di parsare l'output del LLM con una logica a più stadi e resiliente.
        """
        # 1. Tentativo JSON puro
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 2. Tentativo di estrazione blocco {}
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = content[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                pass

        # 3. Tentativo di parsing con Regex da testo "sporco"
        try:
            reply_it_match = re.search(
                r"^(.*?)tags_en:", content, re.DOTALL | re.IGNORECASE
            )
            reply_it = reply_it_match.group(1).strip() if reply_it_match else content.strip()

            # Pulisce reply_it da altre etichette se trovate prima di tags_en
            for label in ["visual_en:", "follow_up_action:"]:
                if label.lower() in reply_it.lower():
                    reply_it = reply_it.split(label)[0].strip()

            tags_en_match = re.search(
                r"tags_en:\s*(\[.*?\])", content, re.DOTALL | re.IGNORECASE
            )
            tags_en = json.loads(tags_en_match.group(1)) if tags_en_match else []

            visual_en_match = re.search(
                r"visual_en:\s*(.*?)(?=\s*follow_up_action:|$)",
                content,
                re.DOTALL | re.IGNORECASE,
            )
            visual_en = visual_en_match.group(1).strip() if visual_en_match else ""

            follow_up_match = re.search(
                r"follow_up_action:\s*(\w+)", content, re.IGNORECASE
            )
            follow_up = follow_up_match.group(1).strip() if follow_up_match else None

            # Se abbiamo estratto qualcosa, ricostruiamo e restituiamo
            if tags_en or visual_en:
                self.log.warning(
                    "Output LLM non in JSON, ma recuperato con Regex: %r", content
                )
                return {
                    "reply_it": reply_it,
                    "tags_en": tags_en,
                    "visual_en": visual_en,
                    "follow_up_action": follow_up,
                }
        except Exception:
            # Se anche il regex fallisce, passiamo al fallback finale
            pass

        # 4. Fallback finale (solo se tutto il resto è fallito)
        self.log.warning(
            "Impossibile parsare l'output LLM in JSON, uso fallback minimale. Contenuto grezzo: %r",
            content,
        )
        return {
            "reply_it": content.strip().split("tags_en:")[0].strip(),
            "tags_en": [],
            "visual_en": "",
            "follow_up_action": None,
        }

    def generate_reply(
        self,
        user_text: str,
        character: Character,
        history: Sequence[ChatMessage],
    ) -> LLMReply:
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

        try:
            resp = requests.post(
                self.endpoint, headers=headers, json=payload, timeout=self.timeout_s
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except (requests.RequestException, KeyError, IndexError, TypeError) as e:
            self.log.error("Errore chiamata o formato risposta LLM: %s", e)
            return LLMReply(
                reply_it="[Mi scuso, ma ho avuto un problema tecnico. Riprova.]"
            )

        obj = self._parse_llm_content(content)

        reply_it = obj.get("reply_it") or ""
        tags_raw = obj.get("tags_en") or []
        if isinstance(tags_raw, list):
            tags_en = [str(t) for t in tags_raw if str(t).strip()]
        else:
            tags_en = [str(tags_raw)] if str(tags_raw).strip() else []
        visual_en = str(obj.get("visual_en") or "")
        follow_up_action = (
            str(obj.get("follow_up_action"))
            if obj.get("follow_up_action") is not None
            else None
        )

        is_fallback = not tags_en and not visual_en

        if not is_fallback:
            tag_count = len(tags_en)
            if tag_count < 8 or tag_count > 12:
                self.log.warning(
                    "tags_en fuori range (8–12): count=%d, tags=%r",
                    tag_count,
                    tags_en,
                )

            visual_word_count = len(visual_en.split())
            if visual_word_count < 24 or visual_word_count > 70:
                self.log.warning(
                    "visual_en fuori range (24–70 parole): count=%d, visual_en=%r",
                    visual_word_count,
                    visual_en,
                )

        return LLMReply(
            reply_it=reply_it,
            tags_en=tags_en,
            visual_en=visual_en,
            follow_up_action=follow_up_action,
            raw_json=obj,
        )
