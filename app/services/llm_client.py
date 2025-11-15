diff - -git
a / app / services / llm_client.py
b / app / services / llm_client.py
index
7e927
c414bd41eb797a31f983ae18e1681efca9a.
.528
cde42b0c3c6fd28d8ee3b980b04ceaf2606fe
100644
--- a / app / services / llm_client.py
+++ b / app / services / llm_client.py


@ @-308

, 82 + 308, 87 @ @


class LLMClient:
    "Timeout LLM dopo %d secondi. Nessuna risposta dal modello.",
    self.timeout_s,

)
# Risposta di fallback leggibile
return LLMReply(
    reply_it="[Scusa, ci sto mettendo troppo a rispondere. Riproviamo tra poco.]",
    tags_en=[],
    visual_en="",
    follow_up_action=None,
    raw_text=raw_text,
)

except Exception as e:
self.log.error("Errore chiamata LLM o formato risposta: %s", e)
# fallback minimale
fallback_text = self._strip_meta_from_reply(raw_text or "")
return LLMReply(
    reply_it=fallback_text
             or "[Scusa, ho avuto un problema tecnico con il modello. Riproviamo tra poco.]",
    tags_en=[],
    visual_en="",
    follow_up_action=None,
    raw_text=raw_text,
)

+        parsed = _parse_structured_text(raw_text or "") or {}
+
reply_it_raw = str(parsed.get("reply_it") or "").strip()
reply_it = self._strip_meta_from_reply(reply_it_raw)

tags_en_raw = parsed.get("tags_en") or []
visual_en = str(parsed.get("visual_en") or "").strip()

if isinstance(tags_en_raw, list):
    tags_en = [str(t).strip() for t in tags_en_raw if str(t).strip()]
else:
    tags_en = [str(tags_en_raw).strip()] if str(tags_en_raw).strip() else []

# piccoli controlli e warning non bloccanti
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

# --- LOG DETTAGLIATO DELL’OUTPUT LLM -------------------------
visual_preview = visual_en.strip()
if len(visual_preview) > 240:
    visual_preview = visual_preview[:240] + "…"

self.log.info(
    "LLM output OK.\n"
    "  reply_it=%r\n"
    "  tags_en(%d)=%r\n"
    "  visual_words=%d\n"
    "  visual_en=%r",
    reply_it,
    len(tags_en),
    tags_en,
    len(visual_en.split()) if visual_en else 0,
    visual_preview,
)
# --------------------------------------------------------------

+
if not reply_it and raw_text:
    +            reply_it = self._strip_meta_from_reply(raw_text)
+
return LLMReply(
    -            reply_it=reply_it or (raw_text or "").strip(),
+            reply_it = reply_it or "[Non ho capito la richiesta, riproviamo.]",
tags_en = tags_en,
visual_en = visual_en,
follow_up_action = None,
raw_text = raw_text,
)

