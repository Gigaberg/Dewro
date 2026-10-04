"""Flask backend for the Material Harmonization webapp.

Serves the Design.md-styled frontend (web/index.html) and exposes the existing
src/ pipeline modules as JSON endpoints. Functionally mirrors the Streamlit app.
"""
from __future__ import annotations

import io
import os
import re

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

from src import data, dedupe, extract, pipeline, standardize

app = Flask(__name__, static_folder="web", static_url_path="")


# --------------------------------------------------------------------------- #
# Static frontend
# --------------------------------------------------------------------------- #
@app.get("/")
def index():
    return send_from_directory("web", "index.html")


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
@app.get("/api/data/overview")
def data_overview():
    df = data.dataset_overview()
    return jsonify(columns=list(df.columns), rows=df.to_dict("records"))


@app.get("/api/data/preview")
def data_preview():
    ds = request.args.get("dataset", "flipkart")
    try:
        if ds == "flipkart":
            df = data.flipkart_subset(limit=50)[
                ["product_name", "brand", "category", "description"]
            ]
            return jsonify(tables=[_table("Flipkart", df)])
        if ds == "abtbuy":
            ab = data.load_abt_buy()
            return jsonify(tables=[
                _table("Abt (left)", ab["left"].head(25)),
                _table("Buy (right)", ab["right"].head(25)),
            ])
        if ds == "amazongoogle":
            ag = data.load_amazon_google()
            return jsonify(tables=[
                _table("Amazon (left)", ag["left"].head(25)),
                _table("Google (right)", ag["right"].head(25)),
            ])
        if ds == "wdc":
            wdc = data.load_wdc("test").head(25).copy()
            wdc["attributes"] = wdc["attributes"].map(
                lambda d: ", ".join(f"{k}: {v}" for k, v in d.items())
            )
            return jsonify(tables=[
                _table("WDC-PAVE", wdc[["category", "raw_text", "attributes"]]),
            ])
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=str(exc)), 500
    return jsonify(error=f"unknown dataset {ds}"), 400


@app.get("/api/flipkart/categories")
def flipkart_categories():
    return jsonify(categories=data.flipkart_categories())


# --------------------------------------------------------------------------- #
# Stage 1 — duplicate detection
# --------------------------------------------------------------------------- #
@app.post("/api/dedupe")
def api_dedupe():
    try:
        body = request.get_json(force=True)
        texts, labels, _ = _resolve_texts(body)
        threshold = float(body.get("threshold", 0.85))
        method = body.get("method", "embeddings")
        if len(texts) < 2:
            return jsonify(error="Need at least 2 descriptions."), 400
        # Cap at 100 items on free-tier to avoid OOM / timeout kills.
        MAX_ITEMS = 100
        if len(texts) > MAX_ITEMS:
            texts = texts[:MAX_ITEMS]
            labels = labels[:MAX_ITEMS]

        res = dedupe.detect_duplicates(texts, threshold=threshold, method=method)
        groups = []
        for gi, group in enumerate(res.duplicate_groups, start=1):
            pairs = res.pairs(group)
            groups.append({
                "id": gi,
                "size": len(group),
                "top": round(pairs[0][2], 3) if pairs else 0.0,
                "members": [labels[i] for i in group],
                "pairs": [
                    {"a": labels[i][:80], "b": labels[j][:80], "sim": round(s, 3)}
                    for i, j, s in pairs
                ],
            })
        return jsonify(
            n_items=res.n_items,
            n_groups=len(res.duplicate_groups),
            n_in_groups=sum(len(g) for g in res.duplicate_groups),
            groups=groups,
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"Dedupe failed: {exc}"), 500


# --------------------------------------------------------------------------- #
# Stage 2 — attribute extraction
# --------------------------------------------------------------------------- #
@app.post("/api/extract")
def api_extract():
    body = request.get_json(force=True)
    source = body.get("source", "text")
    gold = None
    brand_hint = None

    if source == "wdc":
        wdc = data.load_wdc("test")
        idx = max(0, min(int(body.get("index", 0)), len(wdc) - 1))
        row = wdc.iloc[idx]
        text = row["raw_text"]
        gold = row["attributes"]
    elif source == "flipkart":
        fk = data.flipkart_subset(limit=200)
        idx = max(0, min(int(body.get("index", 0)), len(fk) - 1))
        row = fk.iloc[idx]
        text = f"{row['product_name']}. {row['description']}"
        brand_hint = row.get("brand")
    else:
        text = body.get("text", "")

    fields = extract.extract_attributes(text, brand_hint=brand_hint)
    return jsonify(
        text=text,
        spacy=extract.spacy_available(),
        fields=[{"field": k, "value": v} for k, v in fields.items()],
        gold=[{"field": k, "value": v} for k, v in (gold or {}).items()] if gold else None,
    )


# --------------------------------------------------------------------------- #
# Stage 3 — standardization
# --------------------------------------------------------------------------- #
@app.post("/api/standardize")
def api_standardize():
    body = request.get_json(force=True)
    text = body.get("text", "")
    run_t5 = bool(body.get("run_t5", False))
    res = standardize.standardize(text, run_t5=run_t5)
    return jsonify(res)


# --------------------------------------------------------------------------- #
# Stage 4 — full pipeline
# --------------------------------------------------------------------------- #
@app.post("/api/pipeline")
def api_pipeline():
    try:
        body = request.get_json(force=True)
        texts, _, hints = _resolve_texts(body)
        if not texts:
            return jsonify(error="No descriptions provided."), 400
        threshold = float(body.get("threshold", 0.80))
        method = body.get("method", "embeddings")
        run_t5 = bool(body.get("run_t5", False))

        df = pipeline.harmonize(
            texts, threshold=threshold, method=method, run_t5=run_t5, brand_hints=hints,
        )
        return jsonify(
            n_in=len(texts),
            n_records=len(df),
            n_groups=int((df["size"] > 1).sum()) if len(df) else 0,
            columns=list(df.columns),
            rows=df.fillna("").to_dict("records"),
            csv=df.to_csv(index=False),
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"Pipeline failed: {exc}"), 500


# --------------------------------------------------------------------------- #
# CSV upload inspection (for the pipeline "Upload CSV" input)
# --------------------------------------------------------------------------- #
@app.post("/api/csv/inspect")
def csv_inspect():
    f = request.files.get("file")
    if f is None:
        return jsonify(error="No file uploaded."), 400
    try:
        df = pd.read_csv(io.BytesIO(f.read())).head(2000)
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"Could not parse CSV: {exc}"), 400
    return jsonify(
        columns=list(df.columns),
        suggested=_best_text_column(df),
        rows=df.fillna("").astype(str).to_dict("records"),
    )


def _best_text_column(df: pd.DataFrame) -> str | None:
    """Pick the most description-like column: longest avg text, skipping id/numeric."""
    best, best_score = None, -1.0
    for col in df.columns:
        series = df[col].dropna().astype(str)
        if series.empty:
            continue
        # fraction of values that are purely numeric (ids, prices, codes)
        numeric_frac = series.str.fullmatch(r"\s*-?\d+(?:\.\d+)?\s*").mean()
        avg_len = series.str.len().mean()
        name_penalty = 0.0 if re.search(r"id$|^id|price|qty|count", col, re.I) else 1.0
        # prefer long, non-numeric, non-id columns
        score = avg_len * (1.0 - numeric_frac) * name_penalty
        if score > best_score:
            best, best_score = col, score
    return best


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _table(name: str, df: pd.DataFrame) -> dict:
    df = df.fillna("").astype(str)
    return {"name": name, "columns": list(df.columns), "rows": df.to_dict("records")}


def _resolve_texts(body: dict):
    """Return (texts, labels, brand_hints) from a request body.

    Accepts either {category, limit} (Flipkart) or {texts: [...]}.
    """
    if body.get("category"):
        subset = data.flipkart_subset(
            category=body["category"], limit=int(body.get("limit", 150))
        )
        texts = (subset["product_name"] + ". " + subset["description"]).tolist()
        labels = subset["product_name"].tolist()
        hints = subset["brand"].astype(str).tolist()
        return texts, labels, hints
    texts = [str(t).strip() for t in body.get("texts", []) if str(t).strip()]
    return texts, texts, None


if __name__ == "__main__":
    # Hugging Face Spaces (and most PaaS) inject the port via $PORT; HF expects 7860.
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port, debug=False)
