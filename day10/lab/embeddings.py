from __future__ import annotations

import os
from functools import lru_cache
from typing import Iterable, List


DEFAULT_LOCAL_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_JINA_MODEL = "jina-embeddings-v5-text-small"
JINA_API_URL = "https://api.jina.ai/v1/embeddings"


def _normalize_provider(raw: str) -> str:
    provider = (raw or "").strip().lower()
    aliases = {
        "": "sentence_transformers",
        "local": "sentence_transformers",
        "sentence-transformers": "sentence_transformers",
        "sentence_transformers": "sentence_transformers",
        "jina": "jina",
        "jina_api": "jina",
    }
    return aliases.get(provider, provider)


def get_embedding_provider() -> str:
    return _normalize_provider(os.environ.get("EMBEDDING_PROVIDER", "jina"))


def get_embedding_model() -> str:
    provider = get_embedding_provider()
    default_model = DEFAULT_JINA_MODEL if provider == "jina" else DEFAULT_LOCAL_MODEL
    return os.environ.get("EMBEDDING_MODEL", default_model).strip() or default_model


def describe_embedding_runtime() -> str:
    provider = get_embedding_provider()
    model = get_embedding_model()
    return f"provider={provider} model={model}"


def collection_embedding_metadata() -> dict[str, str]:
    return {
        "embedding_provider": get_embedding_provider(),
        "embedding_model": get_embedding_model(),
    }


@lru_cache(maxsize=4)
def _load_sentence_transformer(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def _embed_with_sentence_transformers(texts: List[str]) -> List[List[float]]:
    model = _load_sentence_transformer(get_embedding_model())
    vectors = model.encode(texts, normalize_embeddings=False)
    return [list(map(float, row)) for row in vectors.tolist()]


def _embed_with_jina(texts: List[str], *, task: str) -> List[List[float]]:
    import requests

    api_key = os.environ.get("JINA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing JINA_API_KEY for EMBEDDING_PROVIDER=jina")

    response = requests.post(
        JINA_API_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json={
            "model": get_embedding_model(),
            "input": texts,
            "task": task,
        },
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    rows = sorted(payload.get("data", []), key=lambda item: item.get("index", 0))
    return [item["embedding"] for item in rows]


def embed_texts(texts: Iterable[str], *, task: str) -> List[List[float]]:
    batch = list(texts)
    if not batch:
        return []

    provider = get_embedding_provider()
    if provider == "jina":
        return _embed_with_jina(batch, task=task)
    if provider == "sentence_transformers":
        return _embed_with_sentence_transformers(batch)
    raise ValueError(f"Unsupported embedding provider: {provider}")


def embed_passages(texts: Iterable[str]) -> List[List[float]]:
    return embed_texts(texts, task=os.environ.get("JINA_PASSAGE_TASK", "retrieval.passage"))


def embed_queries(texts: Iterable[str]) -> List[List[float]]:
    return embed_texts(texts, task=os.environ.get("JINA_QUERY_TASK", "retrieval.query"))


def get_chroma_embedding_function():
    from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

    class RuntimeEmbeddingFunction(EmbeddingFunction[Documents]):
        def __call__(self, input: Documents) -> Embeddings:
            return embed_passages(input)

        def embed_query(self, input: Documents) -> Embeddings:
            return embed_queries(input)

        @staticmethod
        def name() -> str:
            return "day10_runtime_embedding"

        @staticmethod
        def build_from_config(config: dict) -> "RuntimeEmbeddingFunction":
            return RuntimeEmbeddingFunction()

        def get_config(self) -> dict:
            return collection_embedding_metadata()

    return RuntimeEmbeddingFunction()
