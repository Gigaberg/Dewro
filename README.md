---
title: Material Description Harmonization
emoji: "#"
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Material Description Harmonization — Prototype

An interactive Streamlit prototype of the pipeline described in the PRD
(*Material Description Harmonization using NLP and Deep Learning*). It collapses
inconsistent free-text material descriptions of the same physical item into one
clean, structured record.

> **Scope:** This is the **functional pipeline** only. The PRD's academic
> research layer — benchmark scoring (Precision/Recall/F1, BLEU/ROUGE),
> hand-labeling, ablations, and the paper — and `t5-small` fine-tuning are
> intentionally omitted.

## Pipeline

| Stage | Method | Module |
|---|---|---|
| **1. Duplicate detection** | `all-MiniLM-L6-v2` embeddings + cosine similarity clustering (TF-IDF baseline included) | `src/dedupe.py` |
| **2. Attribute extraction** | spaCy `en_core_web_sm` NER + regex rule layer (dimensions, standards, grades, materials, units) | `src/extract.py` |
| **3. Standardization** | Rule/unit normalizer (primary) + pretrained `t5-small` cleanup pass | `src/standardize.py` |
| **End-to-end** | descriptions → clusters → per-cluster harmonized record | `src/pipeline.py` |

## Setup

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

First run also downloads `all-MiniLM-L6-v2` (~90 MB) and `t5-small` (~240 MB)
from Hugging Face. Everything runs on CPU.

## Run

Two frontends share the same `src/` pipeline:

**A) Styled web app** (Flask + Design.md aesthetic — Tailwind, glassmorphism):
```bash
python server.py
```
Then open http://127.0.0.1:7860  (override with `PORT=5000 python server.py`)

**B) Streamlit app:**
```bash
python -m streamlit run app.py
```

Both expose the same five views. Tabs:
- **🔗 Full pipeline** — paste descriptions / pick a Flipkart category / upload a
  CSV → harmonized records table (downloadable as CSV).
- **📁 Data** — dataset overview and previews.
- **🔍 Duplicate detection**, **🏷️ Attribute extraction**, **✨ Standardization** —
  each stage, interactively.

## Data

Datasets live under `Data/` (provided):

```
Data/
├── flipkart/flipkart_com-ecommerce_sample.csv     # real Indian e-commerce (dedup)
├── abtbuy/{Abt,Buy,abt_buy_perfectMapping}.csv    # labeled entity-matching pairs
├── amazongoogle/{Amazon,GoogleProducts,...}.csv   # labeled entity-matching pairs
└── wdc/normalized_*.jsonl                          # attribute extraction ground truth
```

## Project layout

```
app.py                 # Streamlit UI
requirements.txt
src/
├── data.py            # dataset loaders
├── dedupe.py          # stage 1
├── extract.py         # stage 2
├── standardize.py     # stage 3
└── pipeline.py        # end-to-end
```
