"""Qdrant collection operations for the document bot.

The Qdrant instance is shared with the website service, so the bot keeps its
own registry (docbot_collections) and only lists what it created.
"""
from ..embeddings import embed_texts
from ..qdrant_client import get_qdrant_client
from ..telegram_bot import collection_exists, is_valid_collection_name

__all__ = ["CollectionError", "create_collection", "collection_points", "is_valid_name"]


class CollectionError(Exception):
    """Collection operation error with a user-friendly message."""


def is_valid_name(name: str) -> bool:
    """Collection names must also be valid Telegram deep-link payloads."""
    return is_valid_collection_name(name)


def create_collection(name: str) -> None:
    """Create an empty Qdrant collection (vector size probed with one embedding)."""
    if collection_exists(name):
        raise CollectionError(f"Коллекция «{name}» уже существует")

    result = embed_texts(["размер вектора для пробного эмбеддинга"])
    embeddings = result[0] if isinstance(result, tuple) else result
    if not embeddings or not embeddings[0]:
        raise CollectionError("Не удалось определить размер вектора (проверьте JINA_API_KEY)")

    try:
        get_qdrant_client().create_collection(
            collection_name=name,
            vectors_config={"size": len(embeddings[0]), "distance": "Cosine"},
        )
    except Exception as e:
        # Concurrent create or network hiccup — treat an existing collection as success.
        if not collection_exists(name):
            raise CollectionError(f"Не удалось создать коллекцию: {e}") from e


def collection_points(name: str) -> int | None:
    """Point count for a collection, or None if it does not exist."""
    try:
        return get_qdrant_client().get_collection(name).points_count
    except Exception:
        return None
