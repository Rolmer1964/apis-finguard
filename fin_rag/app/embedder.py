"""Modelo de embedding local (sentence-transformers) — sem chamada externa.

Substitui o Titan Embed (Bedrock): roda dentro do próprio container, sem
credencial nem conta de nenhum provedor de nuvem. O modelo é pré-baixado no
build da imagem (ver Dockerfile) e carregado uma única vez por processo.
"""

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer


@lru_cache
def _get_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def embed_one(model_name: str, text: str) -> np.ndarray:
    vec = _get_model(model_name).encode(text, normalize_embeddings=True)
    return vec.astype("float32")


def embed_many(model_name: str, texts: list[str]) -> np.ndarray:
    vecs = _get_model(model_name).encode(
        texts, normalize_embeddings=True, show_progress_bar=False
    )
    return vecs.astype("float32")
