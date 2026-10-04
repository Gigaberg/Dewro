"""Dataset loading helpers for the Material Code Harmonization prototype.

All datasets are expected to live under ``Dewro/Data`` (already provided):

    Data/
    ├── flipkart/flipkart_com-ecommerce_sample.csv
    ├── abtbuy/{Abt.csv, Buy.csv, abt_buy_perfectMapping.csv}
    ├── amazongoogle/{Amazon.csv, GoogleProducts.csv, Amzon_GoogleProducts_perfectMapping.csv}
    └── wdc/{normalized_test.jsonl, normalized_train_0.2.jsonl, normalized_train_1.0.jsonl}

These loaders only read/normalize columns; no ML happens here.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

# Data/ lives next to this package's parent (the Dewro project root).
DATA_DIR = Path(__file__).resolve().parent.parent / "Data"


def _require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Expected dataset file not found: {path}")
    return path


# --------------------------------------------------------------------------- #
# Flipkart — real Indian e-commerce listings (duplicate-detection demo)
# --------------------------------------------------------------------------- #
def _top_category(tree: str) -> str:
    """Pull the first category out of Flipkart's JSON-ish category tree string."""
    if not isinstance(tree, str):
        return ""
    # e.g. '["Clothing >> Women\'s Clothing >> ..."]'
    cleaned = tree.strip().lstrip("[").rstrip("]").strip().strip('"')
    first = cleaned.split(">>")[0].strip()
    return first


@lru_cache(maxsize=1)
def load_flipkart() -> pd.DataFrame:
    path = _require(DATA_DIR / "flipkart" / "flipkart_com-ecommerce_sample.csv")
    df = pd.read_csv(path)
    keep = ["uniq_id", "product_name", "description", "brand",
            "product_category_tree", "product_specifications"]
    df = df[[c for c in keep if c in df.columns]].copy()
    df["category"] = df["product_category_tree"].map(_top_category)
    df["product_name"] = df["product_name"].fillna("").astype(str)
    df["description"] = df["description"].fillna("").astype(str)
    return df


def flipkart_categories(min_rows: int = 30) -> list[str]:
    df = load_flipkart()
    counts = df["category"].value_counts()
    return counts[counts >= min_rows].index.tolist()


def flipkart_subset(category: str | None = None, limit: int = 300) -> pd.DataFrame:
    df = load_flipkart()
    if category:
        df = df[df["category"] == category]
    return df.head(limit).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Entity-matching benchmarks (Abt-Buy, Amazon-Google) — labeled dedup pairs
# --------------------------------------------------------------------------- #
def load_abt_buy() -> dict[str, pd.DataFrame]:
    base = DATA_DIR / "abtbuy"
    abt = pd.read_csv(_require(base / "Abt.csv"), encoding="latin-1")
    buy = pd.read_csv(_require(base / "Buy.csv"), encoding="latin-1")
    mapping = pd.read_csv(_require(base / "abt_buy_perfectMapping.csv"))
    return {"left": abt, "right": buy, "mapping": mapping}


def load_amazon_google() -> dict[str, pd.DataFrame]:
    base = DATA_DIR / "amazongoogle"
    amazon = pd.read_csv(_require(base / "Amazon.csv"), encoding="latin-1")
    google = pd.read_csv(_require(base / "GoogleProducts.csv"), encoding="latin-1")
    mapping = pd.read_csv(_require(base / "Amzon_GoogleProducts_perfectMapping.csv"))
    return {"left": amazon, "right": google, "mapping": mapping}


# --------------------------------------------------------------------------- #
# WDC-PAVE — attribute extraction / standardization ground truth
# --------------------------------------------------------------------------- #
def _flatten_target_scores(target_scores: dict) -> dict[str, str]:
    """Reduce WDC-PAVE target_scores to {attribute: normalized_value}.

    Skips attributes whose only value is 'n/a'.
    """
    out: dict[str, str] = {}
    for attr, values in (target_scores or {}).items():
        for value in values:
            if value == "n/a":
                continue
            out[attr] = value
            break
    return out


@lru_cache(maxsize=3)
def load_wdc(split: str = "test") -> pd.DataFrame:
    """split in {'test', 'train_0.2', 'train_1.0'}."""
    fname = {
        "test": "normalized_test.jsonl",
        "train_0.2": "normalized_train_0.2.jsonl",
        "train_1.0": "normalized_train_1.0.jsonl",
    }[split]
    path = _require(DATA_DIR / "wdc" / fname)
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            title = str(rec.get("input_title", "")).strip().strip('"')
            desc = str(rec.get("input_description", "")).strip().strip('"')
            attrs = _flatten_target_scores(rec.get("target_scores", {}))
            rows.append({
                "id": rec.get("id"),
                "category": rec.get("category", ""),
                "title": title,
                "description": desc,
                "raw_text": re.sub(r"\s+", " ", f"{title} {desc}").strip(),
                "attributes": attrs,
            })
    return pd.DataFrame(rows)


def dataset_overview() -> pd.DataFrame:
    """Small summary table used by the Streamlit 'Data' tab."""
    rows = []
    try:
        fk = load_flipkart()
        rows.append(("Flipkart (real Indian e-commerce)", len(fk),
                     "Duplicate detection"))
    except FileNotFoundError:
        rows.append(("Flipkart", 0, "missing"))
    try:
        ab = load_abt_buy()
        rows.append(("Abt-Buy (entity matching)",
                     len(ab["left"]) + len(ab["right"]),
                     f"{len(ab['mapping'])} gold pairs"))
    except FileNotFoundError:
        rows.append(("Abt-Buy", 0, "missing"))
    try:
        ag = load_amazon_google()
        rows.append(("Amazon-Google (entity matching)",
                     len(ag["left"]) + len(ag["right"]),
                     f"{len(ag['mapping'])} gold pairs"))
    except FileNotFoundError:
        rows.append(("Amazon-Google", 0, "missing"))
    try:
        wdc = load_wdc("test")
        rows.append(("WDC-PAVE (attribute extraction)", len(wdc),
                     "NER + standardization"))
    except FileNotFoundError:
        rows.append(("WDC-PAVE", 0, "missing"))
    return pd.DataFrame(rows, columns=["Dataset", "Rows", "Role in pipeline"])
