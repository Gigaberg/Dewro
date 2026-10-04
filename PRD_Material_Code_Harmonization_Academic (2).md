# Project Requirements Document (PRD)
## Material Description Harmonization using NLP and Deep Learning

**Version:** 3.0 (Academic — Semester Project)
**Type:** DL + NLP Course Project with Research Paper
**Environment:** Google Colab (Free Tier, CPU-only)

---

## 1. Problem Statement

Public sector organizations (CPSEs like ONGC, IOCL, NTPC, SAIL) maintain separate material master records. The same physical item is often stored under different codes and free-text descriptions across systems, because each organization's staff describes it differently.

Example:

| Source | Description |
|--------|-------------|
| ONGC | BALL BEARING 6205-2Z SKF |
| IOCL | Bearing Ball 6205 ZZ |
| NTPC | 6205-2Z Deep Groove Ball Bearing |

This is fundamentally a **text understanding and generation problem**: given noisy, inconsistent free-text descriptions of the same underlying object, (1) determine which ones refer to the same item, (2) pull out the structured facts buried in the text, and (3) rewrite them into one consistent form.

This project builds and evaluates a small pipeline that does exactly that, using real, publicly available product-description data, and studies how well each stage performs.

---

## 2. Project Goals

This is a **course project + research paper**, not a product. The goal is to:
1. Apply NLP techniques (sentence embeddings, semantic similarity, NER) to a real-shaped problem
2. Apply a Deep Learning technique (fine-tuning a small sequence-to-sequence model) to a real-shaped problem
3. Evaluate both stages quantitatively, with metrics suitable for a paper
4. Keep everything runnable in a single Google Colab notebook, on CPU, with no external infrastructure

There is no UI, no database, no multi-user workflow, and no deployment. Everything lives in one or a few notebooks plus a short PDF/paper writeup. (Optionally, a lightweight Gradio interface can be added in a single Colab cell purely for live demo purposes — this is not a UI build-out, just a text-in/text-out widget for showing the standardization model working interactively.)

---

## 3. Explicitly Out of Scope

Removed from the original (hackathon-oriented) version, as unnecessary for a research/course project:

- Web frontend (Streamlit/React), backend API (FastAPI)
- Database of any kind (SQLite/PostgreSQL) — data stays in-memory / CSV / pandas DataFrames within the notebook
- User authentication, roles (Data Steward / Procurement Manager / Admin), audit logs
- Deployment (Render/Railway/HF Spaces)
- Dashboard, charts, PDF report generation
- Direct CPSE data acquisition (RTI requests, LinkedIn outreach, tender scraping) — no public CPSE material-master dataset exists, so this is replaced by real public product-data sources (Section 5.1)
- SAP/ERP integration
- "Common National Material Code" generation
- Any notion of cost savings / business ROI metrics

---

## 4. Project Scope (In Scope)

| Component | Description |
|---|---|
| **Dataset Sourcing & Preparation** | Combine three public datasets (real Indian product data + two labeled academic benchmarks) to cover duplicate detection, attribute extraction, and standardization |
| **Duplicate/Near-Duplicate Detection (NLP)** | Sentence embeddings + cosine similarity to cluster descriptions referring to the same item |
| **Attribute Extraction (NLP)** | NER to pull structured fields (brand, material, dimension, standard, grade) out of free text |
| **Description Standardization (DL)** | Fine-tune a small seq2seq model to rewrite a raw description into a standardized/normalized form |
| **Evaluation** | Precision/Recall/F1 for clustering; field-level accuracy for extraction; BLEU/ROUGE for standardization |
| **Research Paper** | Write-up covering method, experiments, results, and limitations |

---

## 5. Methodology

### 5.1 Datasets

No public dataset of real CPSE material master records exists (these are internal ERP tables). Instead, this project uses **three public datasets**, each covering a different stage of the pipeline. Flipkart is the real-world, Indian-context dataset; the other two are established academic benchmarks used as ready-made "answer keys" so that ground truth doesn't have to be built from scratch for every stage.

| Dataset | What it is | Used for |
|---|---|---|
| **Flipkart Products** (Kaggle, e.g. PromptCloudHQ/flipkart-products) | ~20,000 real Indian e-commerce product listings with title, description, category, brand, specifications | Primary, real-world data for duplicate detection (Indian-context test set) |
| **Amazon-Google / Abt-Buy** (entity matching benchmarks, Uni Mannheim CompERBench) | Pairs of product listings from two sources, with a gold-standard label for which pairs refer to the same product | Validates the duplicate-detection method against an established, pre-labeled benchmark before trusting results on hand-labeled Flipkart data |
| **WDC-PAVE** (Web Data Commons — Product Attribute Value Extraction, wbsg-uni-mannheim/wdc-pave) | Product offers from 59 websites with manually verified attribute-value pairs, provided in both raw-extracted and normalized form | Ground truth for attribute extraction (NER evaluation) and training/evaluation pairs for the standardization model |

**Why three datasets instead of one:** each stage of the pipeline needs a different kind of "correct answer," and no single dataset provides all three:
- Duplicate detection needs pairs marked *same item / different item*
- Attribute extraction needs text with the correct fields already pulled out
- Standardization needs raw text paired with its correct clean/normalized form

Flipkart supplies real Indian text but no ready-made labels; Amazon-Google/Abt-Buy and WDC-PAVE supply the labels needed to evaluate rigorously without hand-labeling everything.

### 5.2 Dataset Preparation Workflow

1. **Download** all three datasets into the Colab notebook (Flipkart CSV from Kaggle; Amazon-Google/Abt-Buy and WDC-PAVE from their respective GitHub/benchmark repositories).
2. **Narrow Flipkart** to one or two categories where the same physical item is likely to recur with different wording (e.g., Tools & Hardware, Electrical) — a few hundred to ~1,500 rows.
3. **Hand-label duplicate clusters** on the narrowed Flipkart subset (~200–300 rows) to create an Indian-context evaluation set for duplicate detection.
4. **Use Amazon-Google/Abt-Buy as-is** (already labeled) to validate the duplicate-detection method.
5. **Use WDC-PAVE as-is** (already has verified attribute values, plus normalized versions) for attribute-extraction evaluation and for standardization-model training/evaluation pairs — no manual labeling needed for these two stages.

### 5.3 Duplicate Detection (NLP — no training required)

- Generate sentence embeddings for every description using a small pretrained sentence-transformer (e.g., `all-MiniLM-L6-v2`) — runs comfortably on CPU.
- Compute pairwise cosine similarity between embeddings.
- Cluster descriptions above a similarity threshold (e.g., 0.85) into duplicate groups (thresholded pairwise matching, or agglomerative clustering on the similarity/distance matrix — no need for a production-grade clustering service).
- Test on Amazon-Google/Abt-Buy first (known labels) to confirm the method works, then apply to the hand-labeled Flipkart subset for the Indian-context result.
- Optionally compare against a simple baseline (TF-IDF + cosine similarity, or fuzzy string matching) for a "before/after" comparison point in the paper.

**Example:** *"Boat Rockerz 450 Bluetooth Headphone, Black"* and *"boAt Rockerz 450 Wireless Headset - Black Colour"* → embeddings compared, similarity above threshold → flagged as duplicates.

### 5.4 Attribute Extraction (NLP)

- Use spaCy's pretrained NER (plus a light rule-based/regex layer for domain terms not covered by general-purpose NER) to extract fields such as brand, material, dimension, and standard/spec.
- Evaluate against WDC-PAVE's manually verified attribute-value pairs (field-level accuracy / exact match).
- Feeds into 5.5 as structured input, and is also a standalone result worth reporting in the paper.

**Example:** *"Samsung Galaxy Tab A8, 10.5 inch, 32GB, Grey"* → extracted as `Brand: Samsung, Screen size: 10.5 inch, Storage: 32GB, Color: Grey`, compared against WDC-PAVE's gold answer for the same fields.

### 5.5 Standardization (Deep Learning component)

- Fine-tune a small sequence-to-sequence model — `t5-small` — to map a raw, inconsistent description/attribute value to its standardized/normalized form.
- Training data: WDC-PAVE's raw-extracted → normalized attribute-value pairs (normalization involves name expansion, generalization, unit-of-measurement conversion, and string wrangling — already provided by the benchmark).
- This is the actual **DL** contribution of the project — training/fine-tuning a neural network, as opposed to just calling a pretrained embedding or NER model.
- Keep it CPU-feasible: small model (`t5-small`, ~60M params), short training (a handful of epochs), modest dataset size.
- Evaluate with BLEU/ROUGE against WDC-PAVE's held-out normalized values, plus exact-match rate.

**Example:** raw *"battery 5000mAh"* → normalized *"5000 mAh"*. The model is trained on thousands of such pairs from WDC-PAVE, then tested on unseen raw text.

### 5.6 Evaluation Summary

| Stage | Dataset used for evaluation | Metric |
|---|---|---|
| Duplicate detection | Amazon-Google/Abt-Buy (validation) + Flipkart (Indian-context result) | Precision, Recall, F1 |
| Attribute extraction | WDC-PAVE | Field-level accuracy / exact match |
| Standardization (DL) | WDC-PAVE (normalized) | BLEU, ROUGE, exact-match rate |

Target ranges (adjust once baseline numbers are seen): Precision > 85%, Recall > 80%, F1 > 82% for duplicate detection — a reasonable goal, not a hard requirement.

---

## 6. Technical Setup

| Layer | Choice | Notes |
|---|---|---|
| Environment | Google Colab (Free, CPU) | No GPU dependency anywhere in the pipeline |
| Data handling | pandas, in-memory / CSV | No database |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) | Lightweight, CPU-friendly |
| NER | spaCy (`en_core_web_sm`) + light rule-based layer for domain terms | |
| DL model | HuggingFace `transformers`, `t5-small` | Fine-tuned on CPU; keep epochs/batch size small |
| Evaluation | scikit-learn (precision/recall/F1), `sacrebleu`/`rouge-score` | |
| Output | Notebook + plots/tables for the paper | No dashboard, no export UI |

---

## 7. Deliverables

1. A Google Colab notebook (or a small set of notebooks) implementing the full pipeline: dataset preparation → duplicate detection → attribute extraction → standardization → evaluation
2. The prepared/labeled datasets used (Flipkart subset with hand-labeled clusters, plus references to Amazon-Google/Abt-Buy and WDC-PAVE)
3. A research paper covering: problem motivation, related work (brief), datasets used, method, experiments, results, discussion of limitations, and future work
4. Result tables/plots (precision/recall/F1 for detection; field-level accuracy for extraction; BLEU/ROUGE for standardization; comparison against the TF-IDF baseline)

---

## 8. Suggested Plan (Semester Timeline, Flexible)

| Phase | Work |
|---|---|
| 1 | Download all three datasets; narrow and hand-label the Flipkart subset for duplicate detection |
| 2 | Implement duplicate detection (embeddings + similarity/clustering); validate on Amazon-Google/Abt-Buy; establish TF-IDF baseline; evaluate on Flipkart |
| 3 | Implement attribute extraction (NER + rules); evaluate against WDC-PAVE |
| 4 | Fine-tune `t5-small` on WDC-PAVE normalized pairs for standardization; evaluate (BLEU/ROUGE) |
| 5 | Consolidate results, run ablations if time allows (e.g., different similarity thresholds, with/without rule-based NER layer) |
| 6 | Write and revise the paper; prepare final notebook and datasets for submission |

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| CPU-only training is slow | Keep dataset and model small (`t5-small`, short training runs); test on a tiny subset first before scaling up |
| Domain terms (SCH40, Gr.B, etc.) not recognized by generic NER | Add a lightweight regex/rule layer on top of spaCy for known patterns |
| Flipkart subset too small after narrowing to a category | Widen to 2–3 related categories rather than forcing duplicates that aren't really there, which would make F1 misleadingly easy |
| No public CPSE material-master dataset exists | Use Flipkart as a real, Indian-context proxy domain; state this substitution explicitly as a limitation in the paper |
| Scope creep back toward the original product-style PRD | Stick to the notebook-only, no-UI/DB/deployment scope defined here |

---

**Document End**
