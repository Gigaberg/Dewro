"""Stage 3 — description standardization.

Approach (per PRD 5.5, with fine-tuning deferred):
    * a deterministic rule/unit normalizer does the reliable work the PRD cites —
      spacing unit quantities, normalizing bearing suffixes, expanding common
      abbreviations, title-casing, collapsing whitespace, deduping tokens.
    * pretrained t5-small (NO fine-tuning) runs a light cleanup/paraphrase pass,
      shown alongside the rule output and clearly labeled.

Without fine-tuning the neural output is weak; the rule normalizer is primary.
Everything runs on CPU.
"""
from __future__ import annotations

import re
from functools import lru_cache

T5_MODEL = "t5-small"

# --------------------------------------------------------------------------- #
# Rule / unit normalizer (primary, deterministic)
# --------------------------------------------------------------------------- #
# unit canonical forms: match number+unit (any spacing/case) -> "<num> <unit>"
_UNIT_CANON = {
    "mah": "mAh", "wh": "Wh", "gb": "GB", "tb": "TB", "mb": "MB", "kb": "KB",
    "ghz": "GHz", "mhz": "MHz", "hz": "Hz", "mm": "mm", "cm": "cm",
    "w": "W", "v": "V", "a": "A", "rpm": "RPM", "kg": "kg", "g": "g",
    "sqmm": "sqmm",
}
_UNIT_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(" + "|".join(sorted(_UNIT_CANON, key=len, reverse=True)) + r")\b",
    re.I,
)

_ABBREV = {
    r"\bss\s?304\b": "Stainless Steel 304",
    r"\bss\s?316\b": "Stainless Steel 316",
    r"\bss\b": "Stainless Steel",
    r"\bms\b": "Mild Steel",
    r"\bgi\b": "Galvanized Iron",
    r"\bsch\.?\s?(\d{2,3})\b": r"Schedule \1",
    # grade: require a separator after 'gr'/'grade' so 'Groove', 'grey' etc. don't match
    r"\bgr(?:ade)?[\s.\-]+([A-Za-z]?\d+(?:\.\d+)?|[A-Z])\b": r"Grade \1",
    r"\bdia\.?\b": "diameter",
    r"\bqty\.?\b": "quantity",
    r"\bpcs?\.?\b": "pieces",
}

# bearing closure suffixes -> canonical 2Z / 2RS
_BEARING_SUFFIX = [
    (re.compile(r"\b(\d{4,5})[\s-]?(?:zz|2z)\b", re.I), r"\1-2Z"),
    (re.compile(r"\b(\d{4,5})[\s-]?(?:2rs|rs)\b", re.I), r"\1-2RS"),
]


def normalize_rules(text: str) -> str:
    """Deterministic standardization of a raw description."""
    s = (text or "").strip()
    if not s:
        return ""

    # 1. canonical unit spacing/casing: 5000mAh -> 5000 mAh
    def _unit_sub(m: re.Match) -> str:
        return f"{m.group(1)} {_UNIT_CANON[m.group(2).lower()]}"

    s = _UNIT_RE.sub(_unit_sub, s)

    # 2. bearing suffixes
    for pat, repl in _BEARING_SUFFIX:
        s = pat.sub(repl, s)

    # 3. abbreviation expansion
    for pat, repl in _ABBREV.items():
        s = re.sub(pat, repl, s, flags=re.I)

    # 4. collapse whitespace / stray punctuation spacing
    s = re.sub(r"\s*,\s*", ", ", s)
    s = re.sub(r"\s+", " ", s).strip(" ,;")

    # 5. de-duplicate consecutive repeated words (case-insensitive)
    words = s.split()
    deduped: list[str] = []
    for w in words:
        if not deduped or deduped[-1].lower() != w.lower():
            deduped.append(w)
    s = " ".join(deduped)

    # 6. title-case words that are plain lowercase alpha; keep codes/units intact
    _unit_forms = {v.lower(): v for v in _UNIT_CANON.values()}

    def _case(w: str) -> str:
        if w.lower() in _unit_forms:          # keep canonical unit casing (mm, mAh, GB)
            return _unit_forms[w.lower()]
        if re.fullmatch(r"[a-z]+", w):
            return w.capitalize()
        return w

    return " ".join(_case(w) for w in s.split())


# --------------------------------------------------------------------------- #
# t5-small cleanup pass (secondary, pretrained, no fine-tuning)
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _t5():
    from transformers import T5ForConditionalGeneration, T5TokenizerFast

    tok = T5TokenizerFast.from_pretrained(T5_MODEL)
    model = T5ForConditionalGeneration.from_pretrained(T5_MODEL)
    model.eval()
    return tok, model


def t5_available() -> bool:
    try:
        _t5()
        return True
    except Exception:  # noqa: BLE001
        return False


def t5_rewrite(text: str) -> str:
    """Light paraphrase/cleanup via pretrained t5-small. Illustrative only."""
    text = (text or "").strip()
    if not text:
        return ""
    try:
        import torch

        tok, model = _t5()
        prompt = (
            "Rewrite this product description in clear standard English: " + text
        )
        inputs = tok(prompt, return_tensors="pt", truncation=True, max_length=128)
        with torch.no_grad():
            out = model.generate(
                **inputs, max_new_tokens=64, num_beams=4, early_stopping=True
            )
        return tok.decode(out[0], skip_special_tokens=True).strip()
    except Exception as exc:  # noqa: BLE001
        return f"(t5-small unavailable: {exc})"


def standardize(text: str, run_t5: bool = True) -> dict[str, str]:
    """Return {'raw', 'normalized', 't5'} for a description."""
    result = {"raw": text, "normalized": normalize_rules(text)}
    if run_t5:
        result["t5"] = t5_rewrite(text)
    return result
