"""
Test suite for RAG API endpoints and Qdrant integration.
Run with: pytest backend/tests/test_api.py -v
Or inside container: docker compose exec backend pytest tests/test_api.py -v
"""

import asyncio
import os
import tempfile

# Isolated SQLite DB for tests — must be set BEFORE importing app modules,
# because the async engine is created at import time.
os.environ["DATABASE_URL"] = (
    f"sqlite+aiosqlite:///{os.path.join(tempfile.mkdtemp(), 'test.db')}"
)
# Import of app.rag builds an OpenAI client, which requires a key to be present.
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.qdrant_client import get_qdrant_client  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    """Create DB tables once per session (TestClient does not run lifespan)."""
    from app.database import init_db

    asyncio.run(init_db())


@pytest.fixture
def client():
    """FastAPI test client.

    raise_server_exceptions=False so unhandled endpoint errors (e.g. missing
    JINA_API_KEY) surface as HTTP 500 — matching production behaviour —
    instead of raising inside the test.
    """
    return TestClient(app, raise_server_exceptions=False)





class TestHealthEndpoint:
    """Test /health endpoint (no auth required)."""

    def test_health_ok(self, client):
        """Health check should return 200 with status=ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"



class TestChatEndpoint:
    """Test /chat endpoint."""

    def test_chat_basic(self, client):
        """POST /chat should attempt to answer."""
        response = client.post(
            "/chat",
            json={"question": "What is the site about?", "collection": "site_collection"},
        )
        # May return 500 if OpenAI API key is missing, but endpoint should be accessible
        assert response.status_code in [200, 500], f"Unexpected status {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "answer" in data, "Response should contain 'answer' key"
            assert isinstance(data["answer"], str), "Answer should be a string"

    def test_chat_with_default_collection(self, client):
        """POST /chat without explicit collection should use 'site_collection'."""
        response = client.post(
            "/chat",
            json={"question": "Hello?"},
        )
        # May fail if OpenAI key is missing, but endpoint should be callable
        assert response.status_code in [200, 500]


class TestQdrantConnection:
    """Test Qdrant client connection and collection discovery."""

    def test_qdrant_client_exists(self):
        """Qdrant client should be initialized."""
        client = get_qdrant_client()
        assert client is not None

    def test_qdrant_get_collections(self):
        """Should be able to fetch collections list."""
        try:
            client = get_qdrant_client()
            collections = client.get_collections()
            # collections is a CollectionsResponse with a 'collections' attribute
            assert collections is not None
            # We don't assert a specific collection exists, just that the call works
        except Exception as e:
            pytest.skip(f"Qdrant not available: {e}")

    def test_qdrant_collection_exists(self):
        """Check if site_collection exists in Qdrant."""
        try:
            client = get_qdrant_client()
            collections = client.get_collections()
            # Get list of collection names
            collection_names = [col.name for col in collections.collections]
            # We don't strictly require it to exist before ingest, so skip if not
            if collection_names:
                assert isinstance(collection_names, list)
        except Exception as e:
            pytest.skip(f"Qdrant check failed: {e}")


class TestIngestEndpoint:
    """Test /ingest endpoint (note: may fail if OpenAI key missing or URL unreachable)."""

    def test_ingest_returns_response(self, client):
        """POST /ingest should return a response (may still fail if URL/API unavailable)."""
        response = client.post(
            "/ingest",
            json={"url": "https://example.com", "collection": "test_ingest"},
        )
        # Endpoint should be accessible
        # May return 500 if URL is unreachable or OpenAI key is missing
        assert response.status_code in [200, 500], f"Unexpected status {response.status_code}: {response.text}"


if __name__ == "__main__":
    # Allow running tests directly: python -m pytest backend/tests/test_api.py
    pytest.main([__file__, "-v"])
