"""Stage 2 — attribute extraction.

Approach (per PRD 5.4):
    * spaCy pretrained NER (en_core_web_sm) for general entities (brand/org, etc.)
    * a regex rule layer for domain terms generic NER misses:
      dimensions, standards/specs, grades, materials, and unit-bearing quantities.

Returns a flat {field: value} dict. The regex layer is self-contained, so the
module still produces useful output even if the spaCy model is unavailable.
"""
from __future__ import annotations

import re
from functools import lru_cache

# --------------------------------------------------------------------------- #
# Regex rule layer — domain patterns the PRD calls out (SCH40, Gr.B, 6205-2Z...)
# --------------------------------------------------------------------------- #
# Each entry: field name -> list of compiled patterns. First match wins per field,
# except MULTI fields which collect all matches.
_MATERIALS = [
    "stainless steel", "mild steel", "carbon steel", "cast iron", "galvanized",
    "aluminium", "aluminum", "copper", "brass", "bronze", "nylon", "pvc",
    "polyethylene", "polypropylene", "rubber", "ceramic", "titanium",
    "ss304", "ss316", "ss 304", "ss 316", "lycra", "cotton", "leather",
]

_RULES: dict[str, list[re.Pattern]] = {
    # 6205-2Z, 6205ZZ, 6205 2RS  (bearing-style part codes)
    "bearing_code": [re.compile(r"\b\d{4,5}[\s-]?(?:2?z|zz|2rs|rs)\b", re.I)],
    # schedule / pipe spec
    "schedule": [re.compile(r"\bsch\.?\s?\d{2,3}\b", re.I)],
    # standards: IS 1239, ASTM A106, ANSI B16.5, DIN 933, EN 10025, ISO 9001
    "standard_spec": [
        re.compile(r"\b(?:IS|ASTM|ANSI|DIN|EN|ISO|BS|JIS|API)\s?[-:]?\s?[A-Z]?\d{2,5}(?:[.\-]\d+)*\b", re.I),
    ],
    # grade: Gr.B, Grade 8.8, Class 10.9, GrB
    "grade": [
        re.compile(r"\b(?:gr|grade|class)\.?\s?-?\s?[A-Z]?\d+(?:\.\d+)?\b", re.I),
        re.compile(r"\bgr\.?\s?-?\s?[A-Z]\b", re.I),
    ],
    # thread / metric size: M8, M8 x 40mm, M12x1.5
    "thread_size": [re.compile(r"\bM\d{1,2}(?:\s?[x×]\s?\d+(?:\.\d+)?\s?mm?)?(?:\s?[x×]\s?\d+(?:\.\d+)?)?\b")],
    # dimensions: 10.5 inch, 40mm, 2.5 sqmm, 1/2", 33-1/3
    "dimension": [
        re.compile(r"\b\d+(?:\.\d+)?\s?(?:mm|cm|m|in(?:ch(?:es)?)?|\"|')\b", re.I),
        re.compile(r"\b\d+(?:\.\d+)?\s?sq\.?\s?mm\b", re.I),
    ],
    # capacity / electrical quantities: 32GB, 5000mAh, 200 Watts, 2.0GHz, 230V
    "capacity": [
        re.compile(r"\b\d+(?:\.\d+)?\s?(?:gb|tb|mb|kb|mah|wh)\b", re.I),
        re.compile(r"\b\d+(?:\.\d+)?\s?(?:w|watts?|v|volts?|a|amps?|hz|ghz|mhz|rpm)\b", re.I),
    ],
}


def _regex_fields(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    # single-value fields
    for field, patterns in _RULES.items():
        for pat in patterns:
            m = pat.search(text)
            if m:
                out[field] = m.group(0).strip()
                break
    # material: scan the known-material list
    low = text.lower()
    for mat in _MATERIALS:
        if re.search(rf"\b{re.escape(mat)}\b", low):
            out["material"] = mat
            break
    return out


# --------------------------------------------------------------------------- #
# spaCy NER layer (optional — module degrades gracefully without the model)
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _nlp():
    import spacy

    return spacy.load("en_core_web_sm")


def spacy_available() -> bool:
    try:
        _nlp()
        return True
    except Exception:  # noqa: BLE001
        return False


_CODE_LIKE = re.compile(r"^(?:M\d|\d)|\d{3,}")  # M8, 6205, starts-with-digit...


def _looks_like_brand(text: str) -> bool:
    """Reject NER 'brand' candidates that are really codes, sizes, or materials."""
    t = text.strip()
    if not t or len(t) < 2:
        return False
    if _CODE_LIKE.search(t):
        return False
    if t.lower() in _MATERIALS:
        return False
    # product-ish common nouns that NER sometimes mislabels as ORG
    if re.fullmatch(r"(?i)(copper|steel|cable|bolt|bearing|pipe|wire)(\s\w+)*", t):
        return False
    return True


def _ner_fields(text: str) -> dict[str, str]:
    try:
        doc = _nlp()(text)
    except Exception:  # noqa: BLE001
        return {}
    out: dict[str, str] = {}
    for ent in doc.ents:
        if ent.label_ in ("ORG", "PRODUCT") and "brand" not in out:
            if _looks_like_brand(ent.text):
                out["brand"] = ent.text
    return out


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def extract_attributes(text: str, brand_hint: str | None = None) -> dict[str, str]:
    """Extract structured fields from a free-text material description.

    Regex rules take priority for domain fields; spaCy fills brand/quantity.
    brand_hint (e.g. a dataset's brand column) overrides NER for the brand field.
    """
    text = (text or "").strip()
    if not text:
        return {}

    fields = _regex_fields(text)
    ner = _ner_fields(text)
    for k, v in ner.items():
        fields.setdefault(k, v)

    if brand_hint and str(brand_hint).strip() and str(brand_hint).lower() != "nan":
        fields["brand"] = str(brand_hint).strip()

    # stable, readable ordering
    order = ["brand", "material", "thread_size", "dimension", "capacity",
             "bearing_code", "schedule", "standard_spec", "grade"]
    ordered = {k: fields[k] for k in order if k in fields}
    for k, v in fields.items():
        ordered.setdefault(k, v)
    return ordered
