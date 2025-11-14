# lora_mapping.py — EN keywords + substring matching + trigger text + defaults + max 3 LoRA

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import re

@dataclass(frozen=True)
class LoRAEntry:
    name: str
    weight: float
    category: str      # "utility" | "style" | "realism" | "slider" | "morph" | "nsfw" | "adapter"
    keywords: Tuple[str, ...]          # parole/frasi che attivano il LoRA (match per "contains")
    sdxl_ok: bool = True
    notes: str = ""
    triggers: Tuple[str, ...] = ()     # richiamo testuale da aggiungere al prompt (oltre al token <lora:...>)

CATEGORY_LIMITS: Dict[str, int] = {
    "adapter": 1,
    "utility": 2,
    "realism": 1,
    "style": 1,
    "slider": 1,
    "morph": 1,
    "nsfw": 1,
}
MAX_TOTAL_LORAS = 3

# —— Fallback quando NESSUN LoRA viene scelto (ordina per priorità) —— #
FALLBACKS: List[tuple[str, float]] = [
    ("add_detail",       0.20),
    ("flux_realism_lora",      0.30),
    ("detailed_notrigger", 0.25),
]

# ---------------------------------- #
#              ENTRIES               #
# ---------------------------------- #
LORAS: List[LoRAEntry] = [
    # --- Adapter ---
    LoRAEntry(
        name="ip-adapter-faceid-plusv2_sdxl_lora",
        weight=0.8, category="adapter",
        keywords=("reference face","same person","face match","face reference","identity match","match face","keep identity"),
        notes="Align face to a reference image (IP-Adapter).",
        triggers=("face id adapter",)
    ),

    # --- Utility / Quality ---
    #LoRAEntry(
    #   name="add-detail-xl",
    #  weight=0.4, category="utility",
    # keywords=("detail","details","high detail","micro detail","fine detail","sharp","sharpen","crisp","clarity","texture","high-res","hires","high resolution"),
#   triggers=("add detail xl",)
    #),
    LoRAEntry(
       name="add_detail",
        weight=0.4, category="utility", sdxl_ok=False,
        keywords=("detail","details","high detail","sharp","sharpen","clarity","texture"),
        notes="Non-XL variant.",
        triggers=("add detail",)
    ),
    #LoRAEntry(
    #    name="sharp detailed image (foot focus) v1.1",
    #    weight=0.4, category="utility",
    #    keywords=("sharp","detailed","detail","foot","feet","soles","sole","toe","toes","arch","plantar","foot focus","feet focus"),
    #    notes="Global sharpness; dataset focused on feet.",
#    triggers=("sharp detailed image (foot focus)",)
    # ),
    LoRAEntry(
        name="Hand v2",
        weight=0.7, category="utility",
        keywords=("hand","hands","fingers","finger","palm","palms","grip","grasp","hand pose","hand gesture","gestures"),
        notes="Improves hands/fingers.",
        triggers=("hands detail",)
    ),
    LoRAEntry(
        name="detailed_notrigger",
        weight=0.45, category="utility",
        keywords=("detail","details","micro detail","texture","sharp","clarity","crisp"),
        triggers=("detailed helper",)
    ),
    LoRAEntry(
        name="epiRealismHelper",
        weight=0.4, category="utility",
        keywords=("realism helper","skin detail","skin texture","natural skin","realistic","pores","skin pores"),
        triggers=("realism helper",)
    ),

    # --- Realism / Beautify ---
    #LoRAEntry(
    #   name="flux_realism_lora",
    #   weight=0.5, category="realism",
    #   keywords=("realism","photo realism","photorealistic","lifelike","true to life","natural light","natural lighting","soft light","soft lighting","cinematic lighting"),
#  triggers=("photo realism",)
    #),
    #     LoRAEntry(
    #    name="princess_xl_v1",
    #     weight=0.5, category="realism",
    #     keywords=("beauty","glamour","fairy","fairy-like","soft skin","portrait","beautify","beauty pass","skin smoothing","airbrush","glam"),
    #    notes="Beautify/portrait glamour for SDXL.",
    #     triggers=("princess xl",)
    # ),
    LoRAEntry(
        name="KrekkovLycoXLV2",
        weight=0.5, category="realism",
        keywords=("xl","detail","realism","texture","sharp","crisp","clarity"),
        triggers=("krekkov xl",)
    ),
    LoRAEntry(
        name="SummertimeSagaXL_Pony",
        weight=0.45, category="realism",
        keywords=("toon realism","comic realism","summertime saga","pony","mlp","cel shading realistic"),
        notes="Toon-realism look.",
        triggers=("summertime saga xl",)
    ),

    # --- Artistic styles ---
    LoRAEntry(
        name="Abstract Painting - Style [LoRA] - Pony V6",
        weight=0.6, category="style",
        keywords=("painting","painterly","abstract","brush stroke","oil paint","oil painting","canvas texture","impasto","pony"),
        triggers=("abstract painting style",)
    ),
    LoRAEntry(
        name="Oscar_ILL",
        weight=0.5, category="style",
        keywords=("illustration","illustrative","cartoon","flat shading","line art","comic","posterized"),
        triggers=("illustration style",)
    ),
    LoRAEntry(
        name="g0th1c2XLP",
        weight=0.6, category="style",
        keywords=("goth","gothic","dark","moody","black makeup","punk","alt","alternative"),
        triggers=("gothic style",)
    ),
    LoRAEntry(
        name="MythAnim3Style",
        weight=0.55, category="style",
        keywords=("anime","myth","mythical","fantasy anime","stylized","cel shading"),
        triggers=("myth anime style",)
    ),
    # LoRAEntry(
    #     name="sinfully_stylish_SDXL",
    #     weight=0.55, category="style",
    #     keywords=("fashion","glamour","editorial","runway","vogue","magazine","magazine cover","fashion shoot","polished","glossy"),
    #     triggers=("sinfully stylish",)
    # ),
    LoRAEntry(
        name="Expressive_H-000001",
        weight=0.2, category="style",
        keywords=("expressive","emotional","facial expression","intense gaze","expressive face","expressive eyes"),
        notes="Enhances facial expressiveness; keep low weight.",
        triggers=("expressive face",)
    ),
    LoRAEntry(
        name="perfection style v2d",
        weight=0.5, category="style",
        keywords=("perfect","beauty perfection","studio beauty","beauty retouch","polished look","airbrushed"),
        triggers=("perfection style",)
    ),
    LoRAEntry(
        name="FluxMythP0rtr4itStyle",
        weight=0.55, category="style",
        keywords=("portrait style","myth","oil painting","classical portrait","fine art"),
        triggers=("myth portrait style",)
    ),

    # --- Sliders ---
    # LoRAEntry(

    #     name="milf_slider_v1",
    #    weight=0.6, category="slider",
    #    keywords=("milf","mature woman","curvy","voluptuous","hourglass"),
    #    triggers=("milf slider",)
    # ),
    LoRAEntry(
        name="Pony Realism Slider",
        weight=0.5, category="slider",
        keywords=("pony","mlp","realism"),
        triggers=("pony realism slider",)
    ),
    LoRAEntry(
        name="StS_PonyXL_Detail_Slider_v1.4_iteration_3",
        weight=0.5, category="slider",
        keywords=("pony","xl detail","pony detail","texture","detail slider"),
        triggers=("pony xl detail slider",)
    ),

    # --- Morph (body shape) ---
    LoRAEntry(
        name="huge fake tits XL v3",
        weight=0.5, category="morph",
        keywords=("fake tits","implants","very large breasts","enormous breasts","huge boobs","giant breasts"),
        triggers=("huge fake tits",)
    ),
    LoRAEntry(
        name="Penis Size_alpha1.0_rank4_noxattn_last",
        weight=0.6, category="morph",
        keywords=("penis size","large penis","male nsfw","big penis"),
        triggers=("penis size",)
    ),

    # --- NSFW / Poses ---
    LoRAEntry(
        name="Masturbation-000018",
        weight=0.6, category="nsfw",
        keywords=("masturbation","self play","self pleasure","fingers in","solo play"),
        triggers=("masturbation pose",)
    ),
    LoRAEntry(
        name="shiObjectInsertionV1",
        weight=0.6, category="nsfw",
        keywords=("object insertion","penetration","toy insertion","insert object"),
        triggers=("object insertion",)
    ),
    LoRAEntry(
        name="Bondage_and_the_Anal_Hook",
        weight=0.6, category="nsfw",
        keywords=("anal hook","bondage","bdsm","restraints","shibari"),
        triggers=("anal hook bondage",)
    ),
    LoRAEntry(
        name="sex_Flux_5",
        weight=0.55, category="nsfw",
        keywords=("sex scene","intercourse","vagina","penetrative sex","sexual position","sex pose"),
        triggers=("sex scene",)
    ),
    LoRAEntry(
        name="tablesex_v1.1",
        weight=0.55, category="nsfw",
        keywords=("table sex","on table","table ","table position","tabletop sex"),
        triggers=("table sex",)
    ),
    #LoRAEntry(
    #   name="MatureFemalePony",
    #   weight=0.85, category="nsfw",
    #    keywords=("milf","mature","breast","Luna", "Maria"),
#   triggers=("milf",)
    #),
    LoRAEntry(
        name="povcun-000015",
        weight=0.45, category="nsfw",
        keywords=("2girls","two women","lesbian","lesbian sex", "intimate moment"),
        triggers=("2girls",)
    ),

    # --- Feet / socks focus ---
    # LoRAEntry(
    #   name="SexySocksSoles",
    #   weight=0.55, category="style",
    #   keywords=("socks","stockings","soles","feet","knee-highs","thigh-highs","nylons","hosiery"),
#    triggers=("sexy socks soles",)
    #),
    #LoRAEntry(
    #    name="footjob_pov_flux_v1",
    #    weight=0.55, category="nsfw",
    #    keywords=("footjob","pov","soles","feet job","foot play"),
#  triggers=("footjob pov",)
    #),
]

# ---------- Helpers ----------

def _text_corpus(tags: List[str], visual: str) -> str:
    t = " ".join(tags + ([visual] if visual else [])).lower()
    return t.replace("-", " ").replace("_", " ").replace("/", " ")

def _score_entry(text: str, entry: LoRAEntry) -> int:
    """Conta quante keyword (anche parziali) compaiono nel testo (case-insensitive)."""
    return sum(1 for k in entry.keywords if k and k.lower() in text)

def _strip_version(name: str) -> str:
    # rimuove tail tipo " v1", " v1.1", "_v2", "-10e" ecc.
    s = re.sub(r"[\s_\-]v\d[\w\.\-]*$", "", name, flags=re.IGNORECASE)
    s = re.sub(r"[\s_\-]\d+e$", "", s, flags=re.IGNORECASE)
    return s

def _display_trigger(entry: LoRAEntry) -> str:
    """Sceglie il trigger testuale da aggiungere al prompt.
    Se non presente, deriva un testo leggibile a partire dal nome LoRA."""
    if entry.triggers:
        return entry.triggers[0]
    base = entry.name.replace("_", " ").replace("-", " ")
    base = _strip_version(base).strip()
    return base

def _find_entry_by_name(name: str) -> Optional[LoRAEntry]:
    for e in LORAS:
        if e.name == name:
            return e
    return None

# ---------- API principale ----------

def pick_loras(tags: List[str], visual: str = "", sdxl: bool = True, max_total: int = MAX_TOTAL_LORAS) -> List[LoRAEntry]:
    text = _text_corpus(tags, visual)

    candidates = sorted(
        (e for e in LORAS if (e.sdxl_ok or not sdxl)),
        key=lambda e: (_score_entry(text, e), -0.0001 * e.weight),
        reverse=True
    )

    picked: List[LoRAEntry] = []
    used_per_cat: Dict[str, int] = {k: 0 for k in CATEGORY_LIMITS}

    for e in candidates:
        if len(picked) >= max_total:
            break
        if _score_entry(text, e) == 0:
            continue
        cap = CATEGORY_LIMITS.get(e.category, 1)
        if used_per_cat.get(e.category, 0) >= cap:
            continue
        picked.append(e)
        used_per_cat[e.category] = used_per_cat.get(e.category, 0) + 1

    # Fallback: nessun match? usa i default (rispettando max_total e categorie)
    if not picked:
        for name, w in FALLBACKS:
            if len(picked) >= max_total:
                break
            e = _find_entry_by_name(name)
            if not e:
                continue
            # rispetta i limiti per categoria
            cap = CATEGORY_LIMITS.get(e.category, 1)
            if used_per_cat.get(e.category, 0) >= cap:
                continue
            # crea una "copia" con peso forzato
            picked.append(LoRAEntry(
                name=e.name, weight=w, category=e.category,
                keywords=e.keywords, sdxl_ok=e.sdxl_ok, notes=e.notes, triggers=e.triggers
            ))
            used_per_cat[e.category] = used_per_cat.get(e.category, 0) + 1

    return picked[:max_total]

def lora_prompt_suffix(entries: List[LoRAEntry], include_triggers: bool = True) -> str:
    """Converte i LoRA in stringa: token <lora:...:...> + (opzionale) richiamo testuale.
    Es: ', <lora:sharp detailed image (foot focus) v1.1:0.40>, sharp detailed image (foot focus)'
    """
    if not entries:
        return ""
    tokens = [f"<lora:{e.name}:{e.weight:.2f}>" for e in entries]
    if include_triggers:
        triggers = [_display_trigger(e) for e in entries]
        parts = tokens + triggers
    else:
        parts = tokens
    return ", " + ", ".join(parts)

# ---------- Demo ----------
if __name__ == "__main__":
    demo_tags = ["portrait", "beauty", "hands visible", "sharp", "photorealistic", "soft lighting"]
    demo_visual = "close-up, soft lighting, natural skin, high detail"
    chosen = pick_loras(demo_tags, demo_visual, sdxl=True)
    print("Picked:", [e.name for e in chosen])
    print("Suffix:", lora_prompt_suffix(chosen))
# --- AGGIUNGI IN FONDO A ai/lora_mapping.py ---

def select_loras(tags: list[str], character: str) -> list[tuple[str, float]]:
    """
    Shim per prompt_builder.compose_prompt(...)
    Ritorna [(nome_lora, peso), ...] in base a tags/visual.
    Nota: SD = 1.5 -> sdxl=False
    """
    # se vuoi considerare anche il testo 'visual', passalo qui; ora usiamo solo tags
    entries = pick_loras(tags, visual="", sdxl=False, max_total=3)
    return [(e.name, float(e.weight)) for e in entries]

