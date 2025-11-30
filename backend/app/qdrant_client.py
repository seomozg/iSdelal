from qdrant_client import QdrantClient
import os

QDRANT_HOST = os.getenv('QDRANT_HOST', 'qdrant')
QDRANT_PORT = int(os.getenv('QDRANT_PORT', 6333))

_client = None


def get_qdrant_client():
    global _client
    if _client is None:
        # Modern qdrant-client 1.x uses url parameter
        _client = QdrantClient(url=f'http://{QDRANT_HOST}:{QDRANT_PORT}')
    return _client

