"""Flask backend for the Material Harmonization webapp.

Serves the Design.md-styled frontend (web/index.html) and exposes the existing
src/ pipeline modules as JSON endpoints.

Auto-scaling note
-----------------
The MiniLM embedding model requires loading into RAM and running a forward pass
for every description. On free-tier containers this times out above ~150 items.
For larger inputs the server automatically falls back to TF-IDF cosine similarity,
which handles 1000+ items in under 2 seconds. A `method_used` and `auto_switched`
field are included in the response so the frontend can inform the user.

Lazy imports
------------
All heavy src modules (spaCy, sentence-transformers, torch) are imported on the
first request that needs them — not at startup. This ensures gunicorn passes the
health check immediately without hitting memory limits on cold start.
"""
from __future__ import annotations

import io
import os
import re

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="web", static_url_path="")

# Items above this threshold auto-switch from MiniLM embeddings to TF-IDF.
EMBED_LIMIT = 150

# Lazy module cache — populated on first request.
_src: dict = {}


def _mod(name: str):
    """Return a src module, importing all of them on first call."""
    if not _src:
        from src import data, dedupe, extract, pipeline, standardize
        _src["data"] = data
        _src["dedupe"] = dedupe
        _src["extract"] = extract
        _src["pipeline"] = pipeline
        _src["standardize"] = standardize
    return _src[name]


# --------------------------------------------------------------------------- #
# Health check — responds instantly, no model loading
# --------------------------------------------------------------------------- #
@app.get("/health")
def health():
    return jsonify(status="ok")


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
    try:
        df = _mod("data").dataset_overview()
        return jsonify(columns=list(df.columns), rows=df.to_dict("records"))
    except Exception as exc:  # noqa: BLE001
        import traceback
        return jsonify(error=str(exc), detail=traceback.format_exc()), 500


@app.get("/api/data/preview")
def data_preview():
    ds = request.args.get("dataset", "flipkart")
    try:
        d = _mod("data")
        if ds == "flipkart":
            df = d.flipkart_subset(limit=50)[
                ["product_name", "brand", "category", "description"]
            ]
            return jsonify(tables=[_table("Flipkart", df)])
        if ds == "abtbuy":
            ab = d.load_abt_buy()
            return jsonify(tables=[
                _table("Abt (left)", ab["left"].head(25)),
                _table("Buy (right)", ab["right"].head(25)),
            ])
        if ds == "amazongoogle":
            ag = d.load_amazon_google()
            return jsonify(tables=[
                _table("Amazon (left)", ag["left"].head(25)),
                _table("Google (right)", ag["right"].head(25)),
            ])
        if ds == "wdc":
            wdc = d.load_wdc("test").head(25).copy()
            wdc["attributes"] = wdc["attributes"].map(
                lambda x: ", ".join(f"{k}: {v}" for k, v in x.items())
            )
            return jsonify(tables=[
                _table("WDC-PAVE", wdc[["category", "raw_text", "attributes"]]),
            ])
    except Exception as exc:  # noqa: BLE001
        import traceback
        return jsonify(error=str(exc), detail=traceback.format_exc()), 500
    return jsonify(error=f"unknown dataset {ds}"), 400


@app.get("/api/flipkart/categories")
def flipkart_categories():
    try:
        return jsonify(categories=_mod("data").flipkart_categories())
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=str(exc)), 500


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

        method, auto_switched = _resolve_method(method, len(texts))
        res = _mod("dedupe").detect_duplicates(texts, threshold=threshold, method=method)

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
            method_used=method,
            auto_switched=auto_switched,
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"Dedupe failed: {exc}"), 500


# --------------------------------------------------------------------------- #
# Stage 2 — attribute extraction
# --------------------------------------------------------------------------- #
@app.post("/api/extract")
def api_extract():
    try:
        body = request.get_json(force=True)
        source = body.get("source", "text")
        d = _mod("data")
        ex = _mod("extract")
        gold = None
        brand_hint = None

        if source == "wdc":
            wdc = d.load_wdc("test")
            idx = max(0, min(int(body.get("index", 0)), len(wdc) - 1))
            row = wdc.iloc[idx]
            text = row["raw_text"]
            gold = row["attributes"]
        elif source == "flipkart":
            fk = d.flipkart_subset(limit=200)
            idx = max(0, min(int(body.get("index", 0)), len(fk) - 1))
            row = fk.iloc[idx]
            text = f"{row['product_name']}. {row['description']}"
            brand_hint = row.get("brand")
        else:
            text = body.get("text", "")

        fields = ex.extract_attributes(text, brand_hint=brand_hint)
        return jsonify(
            text=text,
            spacy=ex.spacy_available(),
            fields=[{"field": k, "value": v} for k, v in fields.items()],
            gold=[{"field": k, "value": v} for k, v in (gold or {}).items()] if gold else None,
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"Extract failed: {exc}"), 500


# --------------------------------------------------------------------------- #
# Stage 3 — standardization
# --------------------------------------------------------------------------- #
@app.post("/api/standardize")
def api_standardize():
    try:
        body = request.get_json(force=True)
        text = body.get("text", "")
        run_t5 = bool(body.get("run_t5", False))
        res = _mod("standardize").standardize(text, run_t5=run_t5)
        return jsonify(res)
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"Standardize failed: {exc}"), 500


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

        method = body.get("method", "embeddings")
        method, auto_switched = _resolve_method(method, len(texts))
        run_t5 = bool(body.get("run_t5", False))
        threshold = float(body.get("threshold", 0.80))

        df = _mod("pipeline").harmonize(
            texts, threshold=threshold, method=method, run_t5=run_t5, brand_hints=hints,
        )
        return jsonify(
            n_in=len(texts),
            n_records=len(df),
            n_groups=int((df["size"] > 1).sum()) if len(df) else 0,
            columns=list(df.columns),
            rows=df.fillna("").to_dict("records"),
            csv=df.to_csv(index=False),
            method_used=method,
            auto_switched=auto_switched,
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"Pipeline failed: {exc}"), 500


# --------------------------------------------------------------------------- #
# CSV upload inspection
# --------------------------------------------------------------------------- #
@app.post("/api/csv/inspect")
def csv_inspect():
    f = request.files.get("file")
    if f is None:
        return jsonify(error="No file uploaded."), 400
    try:
        df = pd.read_csv(io.BytesIO(f.read())).head(5000)
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"Could not parse CSV: {exc}"), 400
    return jsonify(
        columns=list(df.columns),
        suggested=_best_text_column(df),
        rows=df.fillna("").astype(str).to_dict("records"),
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _table(name: str, df: pd.DataFrame) -> dict:
    df = df.fillna("").astype(str)
    return {"name": name, "columns": list(df.columns), "rows": df.to_dict("records")}


def _resolve_method(requested: str, n_items: int) -> tuple[str, bool]:
    """Auto-switch to TF-IDF for large inputs to avoid timeout/OOM on free tier."""
    if requested == "embeddings" and n_items > EMBED_LIMIT:
        return "tfidf", True
    return requested, False


def _resolve_texts(body: dict):
    """Return (texts, labels, brand_hints) from a request body."""
    if body.get("category"):
        subset = _mod("data").flipkart_subset(
            category=body["category"], limit=int(body.get("limit", 150))
        )
        texts = (subset["product_name"] + ". " + subset["description"]).tolist()
        labels = subset["product_name"].tolist()
        hints = subset["brand"].astype(str).tolist()
        return texts, labels, hints
    texts = [str(t).strip() for t in body.get("texts", []) if str(t).strip()]
    return texts, texts, None


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
