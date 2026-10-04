"""Material Code Harmonization — interactive prototype (Streamlit).

Pipeline (faithful to the PRD, research/eval layer omitted):
    1. Duplicate detection   (embeddings + cosine similarity)
    2. Attribute extraction  (spaCy NER + regex rules)
    3. Standardization       (pretrained t5-small + rule normalizer)

Stage 0 scaffold: the Data tab is live; the three pipeline tabs are stubs
filled in stage by stage.
"""
from __future__ import annotations

import streamlit as st

import pandas as pd

from src import data, dedupe, extract, pipeline, standardize

st.set_page_config(
    page_title="Material Code Harmonization",
    page_icon="🧩",
    layout="wide",
)

st.title("🧩 Material Description Harmonization")
st.caption(
    "Cluster duplicate material descriptions, extract structured attributes, "
    "and standardize free text — an interactive prototype of the PRD pipeline."
)

with st.expander("ℹ️ About this prototype"):
    st.markdown(
        """
        A three-stage pipeline that harmonizes inconsistent material descriptions:

        1. **Duplicate detection** — sentence embeddings (`all-MiniLM-L6-v2`) + cosine
           similarity clustering group descriptions that refer to the same item.
        2. **Attribute extraction** — spaCy NER + a regex rule layer pull out
           structured fields (brand, material, dimension, standard, grade...).
        3. **Standardization** — a rule/unit normalizer (primary) + pretrained
           `t5-small` cleanup rewrite a raw description into a clean form.

        The **🔗 Full pipeline** tab runs all three end-to-end: many messy
        descriptions → one harmonized record per item.

        *Scope note:* the PRD's academic research layer (benchmark scoring with
        Precision/Recall/F1 & BLEU/ROUGE, hand-labeling, the paper) and t5-small
        fine-tuning are intentionally omitted — this is an interactive prototype of
        the functional pipeline.
        """
    )

tab_pipe, tab_data, tab_dupe, tab_extract, tab_std = st.tabs(
    ["🔗 Full pipeline", "📁 Data", "🔍 Duplicate detection",
     "🏷️ Attribute extraction", "✨ Standardization"]
)

with tab_pipe:
    st.subheader("End-to-end harmonization")
    st.write(
        "Collapse many inconsistent descriptions of the same item into one clean, "
        "structured record: **detect duplicates → extract attributes → standardize**."
    )

    pipe_source = st.radio(
        "Input",
        ["Paste descriptions", "Flipkart category", "Upload CSV"],
        horizontal=True,
        key="pipe_source",
    )

    pipe_texts: list[str] = []
    pipe_hints: list[str] | None = None

    if pipe_source == "Paste descriptions":
        raw = st.text_area(
            "One description per line",
            height=150,
            value="BALL BEARING 6205-2Z SKF\nBearing Ball 6205 ZZ\n"
                  "6205-2Z Deep Groove Ball Bearing\n"
                  "Hex Bolt M8 x 40mm SS304\nStainless Steel Hex Bolt M8 40 mm\n"
                  "Copper Cable 2.5 sqmm",
            key="pipe_text",
        )
        pipe_texts = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    elif pipe_source == "Flipkart category":
        cats = data.flipkart_categories()
        c1, c2 = st.columns(2)
        with c1:
            category = st.selectbox("Category", cats, key="pipe_cat")
        with c2:
            limit = st.slider("Max rows", 20, 300, 100, step=10, key="pipe_limit")
        subset = data.flipkart_subset(category=category, limit=limit)
        pipe_texts = (subset["product_name"] + ". " + subset["description"]).tolist()
        pipe_hints = subset["brand"].astype(str).tolist()
    else:
        up = st.file_uploader("CSV with a text column", type=["csv"], key="pipe_csv")
        if up is not None:
            udf = pd.read_csv(up)
            col = st.selectbox("Description column", list(udf.columns), key="pipe_col")
            pipe_texts = udf[col].fillna("").astype(str).tolist()

    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        pipe_thresh = st.slider("Similarity threshold", 0.50, 0.99, 0.80, 0.01,
                                key="pipe_thresh")
    with pc2:
        pipe_method = st.selectbox(
            "Dedup method", ["embeddings", "tfidf"],
            format_func=lambda m: "Embeddings" if m == "embeddings" else "TF-IDF",
            key="pipe_method",
        )
    with pc3:
        pipe_t5 = st.checkbox("t5-small pass", value=False, key="pipe_t5",
                              help="Slower; rule normalizer runs regardless.")

    if st.button("Run full pipeline", type="primary", key="pipe_run"):
        if len(pipe_texts) < 1:
            st.warning("Add at least one description.")
        else:
            with st.spinner(f"Harmonizing {len(pipe_texts)} descriptions..."):
                hdf = pipeline.harmonize(
                    pipe_texts, threshold=pipe_thresh, method=pipe_method,
                    run_t5=pipe_t5, brand_hints=pipe_hints,
                )
            m1, m2, m3 = st.columns(3)
            m1.metric("Descriptions in", len(pipe_texts))
            m2.metric("Harmonized records", len(hdf))
            m3.metric("Duplicate groups", int((hdf["size"] > 1).sum()) if len(hdf) else 0)

            st.markdown("**Harmonized records** (one per detected item)")
            st.dataframe(hdf, use_container_width=True, hide_index=True)
            st.download_button(
                "Download harmonized CSV",
                hdf.to_csv(index=False).encode("utf-8"),
                file_name="harmonized_records.csv",
                mime="text/csv",
            )

with tab_data:
    st.subheader("Datasets")
    st.write(
        "Three public datasets back the pipeline. Flipkart supplies real, "
        "Indian-context product text; the others provide labeled references."
    )
    try:
        st.dataframe(data.dataset_overview(), use_container_width=True, hide_index=True)
    except Exception as exc:  # noqa: BLE001 - surface any load error to the UI
        st.error(f"Could not load dataset overview: {exc}")

    st.divider()
    st.markdown("**Preview a dataset**")
    choice = st.selectbox(
        "Dataset",
        ["Flipkart", "Abt-Buy", "Amazon-Google", "WDC-PAVE"],
    )
    try:
        if choice == "Flipkart":
            st.dataframe(
                data.flipkart_subset(limit=50)[
                    ["product_name", "brand", "category", "description"]
                ],
                use_container_width=True, hide_index=True,
            )
        elif choice == "Abt-Buy":
            ab = data.load_abt_buy()
            st.write("Left source (Abt)")
            st.dataframe(ab["left"].head(25), use_container_width=True, hide_index=True)
            st.write("Right source (Buy)")
            st.dataframe(ab["right"].head(25), use_container_width=True, hide_index=True)
        elif choice == "Amazon-Google":
            ag = data.load_amazon_google()
            st.write("Left source (Amazon)")
            st.dataframe(ag["left"].head(25), use_container_width=True, hide_index=True)
            st.write("Right source (Google)")
            st.dataframe(ag["right"].head(25), use_container_width=True, hide_index=True)
        else:  # WDC-PAVE
            wdc = data.load_wdc("test").head(25)
            st.dataframe(
                wdc[["category", "raw_text", "attributes"]],
                use_container_width=True, hide_index=True,
            )
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not preview {choice}: {exc}")

with tab_dupe:
    st.subheader("Duplicate / near-duplicate detection")
    st.write(
        "Group descriptions that refer to the same physical item. Descriptions are "
        "embedded and clustered by cosine similarity."
    )

    src_col, opt_col = st.columns([3, 2])
    with src_col:
        source = st.radio(
            "Input",
            ["Flipkart category", "Paste my own descriptions"],
            horizontal=True,
            key="dup_source",
        )
    with opt_col:
        method = st.selectbox(
            "Method",
            ["embeddings", "tfidf"],
            format_func=lambda m: "Embeddings (all-MiniLM-L6-v2)" if m == "embeddings"
            else "TF-IDF baseline",
            key="dup_method",
        )

    texts: list[str] = []
    labels: list[str] = []

    if source == "Flipkart category":
        cats = data.flipkart_categories()
        c1, c2 = st.columns(2)
        with c1:
            category = st.selectbox("Category", cats, key="dup_cat")
        with c2:
            limit = st.slider("Max rows", 20, 500, 150, step=10, key="dup_limit")
        subset = data.flipkart_subset(category=category, limit=limit)
        # Name + description gives the embedder the most signal.
        texts = (subset["product_name"] + ". " + subset["description"]).tolist()
        labels = subset["product_name"].tolist()
    else:
        raw = st.text_area(
            "One description per line",
            height=160,
            placeholder="BALL BEARING 6205-2Z SKF\nBearing Ball 6205 ZZ\n"
                        "6205-2Z Deep Groove Ball Bearing\nHex Bolt M8 x 40mm SS304",
            key="dup_text",
        )
        texts = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        labels = texts

    threshold = st.slider(
        "Similarity threshold", 0.50, 0.99, 0.85, step=0.01, key="dup_thresh",
        help="Pairs at or above this cosine similarity are treated as the same item.",
    )

    if st.button("Find duplicates", type="primary", key="dup_run"):
        if len(texts) < 2:
            st.warning("Need at least 2 descriptions.")
        else:
            with st.spinner(f"Embedding {len(texts)} descriptions and clustering..."):
                result = dedupe.detect_duplicates(texts, threshold=threshold, method=method)

            m1, m2, m3 = st.columns(3)
            m1.metric("Items", result.n_items)
            m2.metric("Duplicate groups", len(result.duplicate_groups))
            m3.metric(
                "Items in a group",
                sum(len(g) for g in result.duplicate_groups),
            )

            if not result.duplicate_groups:
                st.info("No duplicate groups at this threshold. Try lowering it.")
            for gi, group in enumerate(result.duplicate_groups, start=1):
                pairs = result.pairs(group)
                top = pairs[0][2] if pairs else 0.0
                with st.expander(
                    f"Group {gi} — {len(group)} items (top similarity {top:.2f})",
                    expanded=gi <= 3,
                ):
                    st.dataframe(
                        pd.DataFrame({"description": [labels[i] for i in group]}),
                        use_container_width=True, hide_index=True,
                    )
                    if len(group) > 2:
                        st.caption("Pairwise similarity")
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "A": labels[i][:60],
                                    "B": labels[j][:60],
                                    "similarity": round(s, 3),
                                }
                                for i, j, s in pairs
                            ]
                        ),
                        use_container_width=True, hide_index=True,
                    )

with tab_extract:
    st.subheader("Attribute extraction")
    st.write(
        "Pull structured fields (brand, material, dimension, standard, grade...) out "
        "of a free-text description using spaCy NER + a domain regex rule layer."
    )
    if not extract.spacy_available():
        st.warning(
            "spaCy model `en_core_web_sm` not found — regex rules still work. "
            "Install with: `python -m spacy download en_core_web_sm`"
        )

    ex_source = st.radio(
        "Input",
        ["Type a description", "Pick a WDC-PAVE row", "Pick a Flipkart row"],
        horizontal=True,
        key="ex_source",
    )

    ex_text = ""
    brand_hint = None
    gold = None

    if ex_source == "Type a description":
        ex_text = st.text_input(
            "Description",
            value="BALL BEARING 6205-2Z SKF, SS304, M8 x 40mm, Gr.B, SCH40",
            key="ex_text",
        )
    elif ex_source == "Pick a WDC-PAVE row":
        wdc = data.load_wdc("test")
        idx = st.number_input(
            "Row", 0, len(wdc) - 1, 0, key="ex_wdc_idx",
        )
        row = wdc.iloc[int(idx)]
        ex_text = row["raw_text"]
        gold = row["attributes"]
        st.text_area("Raw text", ex_text, height=100, disabled=True, key="ex_wdc_text")
    else:
        fk = data.flipkart_subset(limit=200)
        idx = st.number_input(
            "Row", 0, len(fk) - 1, 0, key="ex_fk_idx",
        )
        row = fk.iloc[int(idx)]
        ex_text = f"{row['product_name']}. {row['description']}"
        brand_hint = row.get("brand")
        st.text_area("Raw text", ex_text, height=100, disabled=True, key="ex_fk_text")

    if st.button("Extract attributes", type="primary", key="ex_run"):
        fields = extract.extract_attributes(ex_text, brand_hint=brand_hint)
        if not fields:
            st.info("No attributes found.")
        else:
            extracted_df = pd.DataFrame(
                {"field": list(fields.keys()), "value": list(fields.values())}
            )
            if gold:
                st.markdown("**Extracted vs WDC-PAVE gold** (illustrative, not scored)")
                gold_df = pd.DataFrame(
                    {"field": list(gold.keys()), "gold value": list(gold.values())}
                )
                cL, cR = st.columns(2)
                with cL:
                    st.caption("Extracted (this pipeline)")
                    st.dataframe(extracted_df, use_container_width=True, hide_index=True)
                with cR:
                    st.caption("WDC-PAVE gold attributes")
                    st.dataframe(gold_df, use_container_width=True, hide_index=True)
            else:
                st.dataframe(extracted_df, use_container_width=True, hide_index=True)

with tab_std:
    st.subheader("Description standardization")
    st.write(
        "Rewrite a raw, inconsistent description into a clean, standardized form. "
        "A deterministic rule/unit normalizer does the reliable work; pretrained "
        "t5-small adds a light cleanup pass."
    )
    st.caption(
        "Note: t5-small is used **without fine-tuning**, so its rewrite is "
        "illustrative — the rule normalizer is the dependable output. "
        "Fine-tuning on WDC-PAVE is the faithful-but-heavier path we deferred."
    )

    std_text = st.text_input(
        "Raw description",
        value="battery 5000mAh, SS304, 6205 ZZ, SCH40, qty 10 pcs",
        key="std_text",
    )
    run_t5 = st.checkbox("Also run t5-small cleanup pass", value=True, key="std_t5")

    if st.button("Standardize", type="primary", key="std_run"):
        with st.spinner("Normalizing..."):
            res = standardize.standardize(std_text, run_t5=run_t5)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Raw**")
            st.code(res["raw"], language=None)
        with c2:
            st.markdown("**Normalized (rules)**")
            st.success(res["normalized"])
        if run_t5 and "t5" in res:
            st.markdown("**t5-small cleanup (illustrative)**")
            st.info(res["t5"])
