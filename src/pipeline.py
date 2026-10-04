"""Stage 4 — end-to-end harmonization pipeline.

Ties the three stages together:
    descriptions -> duplicate clusters -> per-cluster canonical record
                    (representative description, standardized form, attributes)

Produces one "harmonized record" per cluster, which is the PRD's core story:
collapse many inconsistent descriptions of the same item into a single clean one.
"""
from __future__ import annotations

import pandas as pd

from . import dedupe, extract, standardize


def _representative(texts: list[str], group: list[int]) -> int:
    """Pick the cluster's representative = the longest (most informative) member."""
    return max(group, key=lambda i: len(texts[i]))


def harmonize(
    texts: list[str],
    threshold: float = 0.85,
    method: str = "embeddings",
    run_t5: bool = False,
    brand_hints: list[str] | None = None,
) -> pd.DataFrame:
    """Run the full pipeline and return one harmonized record per cluster.

    Columns: cluster, size, members, representative, standardized, <attributes...>
    """
    texts = [t if isinstance(t, str) else "" for t in texts]
    if not texts:
        return pd.DataFrame()

    result = dedupe.detect_duplicates(texts, threshold=threshold, method=method)

    records = []
    # Order clusters: multi-item duplicate groups first (largest first), then singletons.
    ordered = sorted(result.clusters, key=lambda c: (-len(c), c[0]))
    for cid, group in enumerate(ordered, start=1):
        rep_idx = _representative(texts, group)
        rep_text = texts[rep_idx]
        hint = brand_hints[rep_idx] if brand_hints else None
        attrs = extract.extract_attributes(rep_text, brand_hint=hint)
        std = standardize.standardize(rep_text, run_t5=run_t5)

        rec = {
            "cluster": cid,
            "size": len(group),
            "members": " | ".join(texts[i] for i in group),
            "representative": rep_text,
            "standardized": std["normalized"],
        }
        rec.update(attrs)
        records.append(rec)

    return pd.DataFrame(records)
