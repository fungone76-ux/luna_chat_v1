# file: app/services/sd_client.py

from __future__ import annotations

import base64
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from app.core.settings import load_app_config


class SDClient:
    """
    Client minimale per Automatic1111 / Forge (/sdapi/v1/txt2img).

    - Usa i parametri da config.app_config.json.sd
    - Salva i PNG in storage/images
    """

    def __init__(self) -> None:
        self.log = logging.getLogger(self.__class__.__name__)
        cfg = load_app_config()
        sd_cfg = cfg.sd
        paths = cfg.paths

        self.enabled: bool = sd_cfg.enabled
        self.autodetect: bool = sd_cfg.autodetect
        self.prefer_ports = sd_cfg.prefer_ports or []

        # base_url già include la porta (es. 7860)
        self.base_url = sd_cfg.base_url.rstrip("/")
        self.txt2img_url = f"{self.base_url}/sdapi/v1/txt2img"

        # parametri da config
        self.default_steps = sd_cfg.default_steps
        self.default_cfg_scale = sd_cfg.cfg_scale
        self.default_sampler = sd_cfg.sampler

        # risoluzioni (per ora usiamo single; multi lo useremo quando faremo il multi-persona)
        self.single_width = sd_cfg.width_single or sd_cfg.width
        self.single_height = sd_cfg.height_single or sd_cfg.height
        self.multi_width = sd_cfg.width_multi or sd_cfg.width
        self.multi_height = sd_cfg.height_multi or sd_cfg.height

        self.timeout_s = sd_cfg.timeout_s

        self.images_dir: Path = paths.images_dir
        self.images_dir.mkdir(parents=True, exist_ok=True)

        self.log.info(
            "SDClient inizializzato: enabled=%s, txt2img_url=%s, steps=%d, cfg=%.2f, sampler=%s, single=%dx%d, timeout=%ds",
            self.enabled,
            self.txt2img_url,
            self.default_steps,
            self.default_cfg_scale,
            self.default_sampler,
            self.single_width,
            self.single_height,
            self.timeout_s,
        )

    def txt2img(
        self,
        prompt: str,
        negative: str,
        seed: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Manda una richiesta txt2img e salva il primo PNG in storage/images.
        Ritorna dict con almeno 'image_path' (o None se fallisce).
        """
        if not self.enabled:
            self.log.warning("SDClient chiamato ma SD è disabilitato in config.")
            return {"image_path": None, "error": "sd_disabled"}

        # Se width/height non sono specificati, usiamo la risoluzione single
        if width is None or height is None:
            w = self.single_width
            h = self.single_height
        else:
            w = width
            h = height

        payload: Dict[str, Any] = {
            "prompt": prompt,
            "negative_prompt": negative,
            "steps": self.default_steps,
            "cfg_scale": self.default_cfg_scale,
            "sampler_name": self.default_sampler,
            "width": w,
            "height": h,
            "seed": seed if seed is not None else -1,
        }

        self.log.debug(
            "Chiamata SD txt2img: url=%s, w=%d, h=%d, steps=%d, cfg_scale=%.2f, sampler=%s",
            self.txt2img_url,
            w,
            h,
            self.default_steps,
            self.default_cfg_scale,
            self.default_sampler,
        )

        try:
            resp = requests.post(
                self.txt2img_url,
                json=payload,
                timeout=self.timeout_s,
            )
            resp.raise_for_status()
        except Exception as e:
            self.log.error("Errore HTTP chiamando txt2img: %s", e)
            return {"image_path": None, "error": str(e)}

        try:
            data = resp.json()
        except Exception as e:
            self.log.error("Risposta SD non JSON: %s", e)
            return {"image_path": None, "error": "invalid_json"}

        images = data.get("images") or []
        if not images:
            self.log.error("Nessuna immagine restituita da SD: %s", data)
            return {"image_path": None, "error": "no_images"}

        img_b64 = str(images[0])
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[-1]

        try:
            raw = base64.b64decode(img_b64)
        except Exception as e:
            self.log.error("Errore nel decodificare base64: %s", e)
            return {"image_path": None, "error": "b64_decode_failed"}

        ts = int(time.time())
        filename = f"sd_{ts}.png"
        out_path = self.images_dir / filename

        try:
            with out_path.open("wb") as f:
                f.write(raw)
        except Exception as e:
            self.log.error("Errore scrivendo file immagine: %s", e)
            return {"image_path": None, "error": "write_failed"}

        self.log.info("Immagine generata: %s", out_path)
        return {"image_path": str(out_path)}
