"""Stage 1 — duplicate / near-duplicate detection.

Approach (per PRD 5.3):
    * embed each description with a small sentence-transformer (all-MiniLM-L6-v2)
    * compute pairwise cosine similarity
    * group descriptions whose similarity >= threshold into clusters
      (connected components over the thresholded similarity graph)

A TF-IDF + cosine baseline is included for an optional "before/after" comparison.
Everything runs on CPU.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np

EMBED_MODEL = "all-MiniLM-L6-v2"


# --------------------------------------------------------------------------- #
# Models (cached so Streamlit reruns don't reload)
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL)


def embed(texts: list[str]) -> np.ndarray:
    """Return L2-normalized embeddings so dot product == cosine similarity."""
    model = _embedder()
    emb = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return emb


def _tfidf_embed(texts: list[str]) -> np.ndarray:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    mat = vec.fit_transform(texts)
    return normalize(mat).toarray()


# --------------------------------------------------------------------------- #
# Similarity + clustering
# --------------------------------------------------------------------------- #
def cosine_matrix(emb: np.ndarray) -> np.ndarray:
    """Pairwise cosine similarity for row-normalized embeddings."""
    sim = emb @ emb.T
    return np.clip(sim, -1.0, 1.0)


def _connected_components(adj: np.ndarray) -> list[list[int]]:
    """Group indices connected (directly or transitively) in a boolean adjacency."""
    n = adj.shape[0]
    seen = np.zeros(n, dtype=bool)
    groups: list[list[int]] = []
    for start in range(n):
        if seen[start]:
            continue
        stack = [start]
        comp = []
        seen[start] = True
        while stack:
            node = stack.pop()
            comp.append(node)
            neighbors = np.where(adj[node] & ~seen)[0]
            for nb in neighbors:
                seen[nb] = True
                stack.append(int(nb))
        groups.append(sorted(comp))
    return groups


@dataclass
class DedupeResult:
    texts: list[str]
    sim: np.ndarray
    threshold: float
    clusters: list[list[int]] = field(default_factory=list)       # all components
    duplicate_groups: list[list[int]] = field(default_factory=list)  # size >= 2

    @property
    def n_items(self) -> int:
        return len(self.texts)

    @property
    def n_clusters(self) -> int:
        return len(self.clusters)

    def pairs(self, group: list[int]) -> list[tuple[int, int, float]]:
        """Pairwise (i, j, score) within a group, sorted high -> low."""
        out = []
        for a_pos in range(len(group)):
            for b_pos in range(a_pos + 1, len(group)):
                i, j = group[a_pos], group[b_pos]
                out.append((i, j, float(self.sim[i, j])))
        out.sort(key=lambda t: t[2], reverse=True)
        return out


def detect_duplicates(
    texts: list[str],
    threshold: float = 0.85,
    method: str = "embeddings",
) -> DedupeResult:
    """Cluster texts into duplicate groups above the similarity threshold.

    method: "embeddings" (all-MiniLM-L6-v2) or "tfidf" (baseline).
    """
    texts = [t if isinstance(t, str) else "" for t in texts]
    if not texts:
        return DedupeResult(texts=[], sim=np.zeros((0, 0)), threshold=threshold)

    emb = _tfidf_embed(texts) if method == "tfidf" else embed(texts)
    sim = cosine_matrix(emb)

    adj = sim >= threshold
    np.fill_diagonal(adj, False)

    clusters = _connected_components(adj)
    dup_groups = [c for c in clusters if len(c) >= 2]
    dup_groups.sort(key=len, reverse=True)

    return DedupeResult(
        texts=texts,
        sim=sim,
        threshold=threshold,
        clusters=clusters,
        duplicate_groups=dup_groups,
    )
