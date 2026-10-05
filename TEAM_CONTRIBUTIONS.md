# Team Contributions — Material Description Harmonization

Project: an NLP + Deep Learning pipeline that harmonizes inconsistent free-text
material descriptions (detect duplicates → extract attributes → standardize),
delivered as an interactive web app (Flask API + Tailwind frontend) and a
Streamlit app, both sharing one pipeline in `src/`.

Work is divided across 4 members by specialization. Each section lists the
components owned, the files, the key technical work, and a ready-to-paste
submission statement.

---

## Member 1 (Nayan Utkarsh) — AI/ML  (Deep Learning & Semantic Modeling)

**Owns:** the neural / deep-learning core of the pipeline.

**Files:** `src/standardize.py`, embedding model integration in `src/dedupe.py`

**Key work**
- Integrated the **t5-small sequence-to-sequence model** (HuggingFace Transformers)
  for description standardization — the project's deep-learning component:
  tokenizer + model loading, prompt construction, beam-search generation
  (`num_beams=4`), CPU-feasible inference, and model caching.
- Integrated the **`all-MiniLM-L6-v2` sentence-transformer** used to turn each
  description into a semantic embedding for similarity comparison.
- Model-selection and feasibility analysis: choosing small models that run on
  CPU (Colab free tier), batching, L2-normalized embeddings so dot product = cosine.
- Documented the DL contribution and the fine-tuning trade-off (pretrained t5-small
  used as an illustrative cleanup pass; fine-tuning on WDC-PAVE noted as future work).

---

## Member 2 (Priyanshu Sithole) — Cyber Security  (Secure Backend, API & Application Hardening)

**Owns:** the backend service, API contract, and application security.

**Files:** `server.py`, security-relevant logic in `web/app.js`

**Key work**
- Designed and built the **Flask REST API** exposing the pipeline as JSON endpoints
  (`/api/pipeline`, `/api/dedupe`, `/api/extract`, `/api/standardize`, `/api/data/*`,
  `/api/csv/inspect`), with consistent request/response contracts and HTTP error codes.
- **File-upload security** for the CSV feature: safe parsing via `io.BytesIO`,
  a **2000-row ingestion cap** to bound resource use, graceful parse-error handling,
  and the auto-detection of the intended text column (hardening against malformed input).
- **XSS prevention** on the frontend: every value rendered into the DOM is run
  through an HTML-escaping function (`esc()`), so untrusted CSV/dataset content
  cannot inject markup.
- Input validation (minimum item counts, index clamping for dataset rows),
  localhost-only binding (`127.0.0.1`), debug disabled, and a `.gitignore` that
  keeps data and secrets out of version control.
- Diagnosed a **stale-process / port-binding issue** (two servers bound to port
  5000 serving different code) and documented a safe restart procedure.

---

## Member 3 (Shlok) — Data Science  (Data Engineering & Duplicate Detection)

**Owns:** dataset sourcing/preparation and the duplicate-detection stage.

**Files:** `src/data.py`, `src/dedupe.py`

**Key work**
- **Dataset engineering** for four public datasets: Flipkart (real Indian
  e-commerce), Abt-Buy and Amazon-Google (entity-matching benchmarks), and
  WDC-PAVE (attribute extraction). Wrote robust loaders handling encodings,
  Flipkart's nested category-tree parsing, category narrowing, and flattening
  WDC-PAVE's `target_scores` into clean attribute dictionaries.
- Built the **duplicate-detection algorithm** (`src/dedupe.py`): pairwise cosine
  similarity, threshold-based grouping via a **connected-components clustering**
  over the similarity graph, and a **TF-IDF baseline** for before/after comparison.
- Exploratory analysis: dataset overview/summary statistics, choosing the
  similarity threshold, and analyzing over-/under-merging behavior.

---

## Member 4 (Shivansh Shaurya) — Data Science  (Attribute Extraction, Normalization & Pipeline Integration)

**Owns:** the attribute-extraction stage, the rule-based normalizer, and the
end-to-end pipeline.

**Files:** `src/extract.py`, rule layer in `src/standardize.py`, `src/pipeline.py`

**Key work**
- Built **attribute extraction** (`src/extract.py`): spaCy `en_core_web_sm` NER
  combined with a **domain-specific regex rule layer** for terms generic NER misses
  — materials, thread sizes (`M8 x 40mm`), dimensions, capacities (`5000mAh`, `32GB`),
  bearing codes (`6205-2Z`), schedules (`SCH40`), standards (`IS 1239`), grades (`Gr.B`).
  Added brand-candidate filtering to suppress false positives.
- Built the **rule/unit normalizer** inside standardization: unit canonicalization
  (`5000mAh` → `5000 mAh`), abbreviation expansion (`SS304` → `Stainless Steel 304`),
  whitespace/casing cleanup, and bearing-suffix normalization.
- Built the **end-to-end pipeline** (`src/pipeline.py`): orchestrates dedupe →
  representative selection (longest/most-informative member) → extraction →
  standardization, producing one harmonized record per cluster with a downloadable CSV.
- Results analysis and worked examples validating each stage against PRD examples.

---

## Shared / joint work

- **Frontend & presentation:** the Streamlit app (`app.py`) and the Tailwind/
  Design.md-styled web UI (`web/index.html`, `web/app.js`) were built jointly;
  Member 2 owns the API/security side, Members 3 & 4 the data-facing views,
  Member 1 the model-output displays.
- **Documentation:** `README.md`, this contributions file, and the shared scope
  decision to omit the academic research/evaluation layer per the project brief.

## Component → owner quick map

| Component | File(s) | Owner |
|---|---|---|
| t5-small standardization (DL) | `src/standardize.py` | M1 (AI/ML) |
| Sentence embeddings (MiniLM) | `src/dedupe.py` | M1 (AI/ML) |
| Flask API + security + uploads | `server.py`, `web/app.js` (esc) | M2 (Cyber) |
| Dataset loaders / prep | `src/data.py` | M3 (DS) |
| Duplicate detection + TF-IDF baseline | `src/dedupe.py` | M3 (DS) |
| Attribute extraction (NER + regex) | `src/extract.py` | M4 (DS) |
| Rule/unit normalizer | `src/standardize.py` | M4 (DS) |
| End-to-end pipeline | `src/pipeline.py` | M4 (DS) |
| Web/Streamlit UI | `web/*`, `app.py` | Joint |
