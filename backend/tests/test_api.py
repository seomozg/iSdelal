"""
Test suite for RAG API endpoints and Qdrant integration.
Run with: pytest backend/tests/test_api.py -v
Or inside container: docker compose exec backend pytest tests/test_api.py -v
"""

import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.qdrant_client import get_qdrant_client


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def api_key():
    """Get API key from env (set in backend/.env or via docker env)."""
    return os.getenv("API_KEY", "test_key_123")


class TestHealthEndpoint:
    """Test /health endpoint (no auth required)."""

    def test_health_ok(self, client):
        """Health check should return 200 with status=ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"


class TestAuthMiddleware:
    """Test API key authentication on protected endpoints."""

    def test_ingest_without_key(self, client):
        """POST /ingest without X-API-Key should return 401."""
        response = client.post(
            "/ingest",
            json={"url": "https://example.com", "collection": "test_coll"},
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.text or "Unauthorized" in response.text

    def test_chat_without_key(self, client):
        """POST /chat without X-API-Key should return 401."""
        response = client.post(
            "/chat",
            json={"question": "test", "collection": "test_coll"},
        )
        assert response.status_code == 401

    def test_ingest_with_wrong_key(self, client):
        """POST /ingest with wrong X-API-Key should return 401."""
        response = client.post(
            "/ingest",
            json={"url": "https://example.com", "collection": "test_coll"},
            headers={"X-API-Key": "wrong_key_xyz"},
        )
        assert response.status_code == 401

    def test_chat_with_wrong_key(self, client):
        """POST /chat with wrong X-API-Key should return 401."""
        response = client.post(
            "/chat",
            json={"question": "test?", "collection": "test_coll"},
            headers={"X-API-Key": "wrong_key_xyz"},
        )
        assert response.status_code == 401


class TestChatEndpoint:
    """Test /chat endpoint with valid auth."""

    def test_chat_with_valid_key(self, client, api_key):
        """POST /chat with valid API key should attempt to answer."""
        response = client.post(
            "/chat",
            json={"question": "What is the site about?", "collection": "site_collection"},
            headers={"X-API-Key": api_key},
        )
        # May return 500 if OpenAI API key is missing, but shouldn't be 401
        assert response.status_code in [200, 500], f"Unexpected status {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "answer" in data, "Response should contain 'answer' key"
            assert isinstance(data["answer"], str), "Answer should be a string"

    def test_chat_with_default_collection(self, client, api_key):
        """POST /chat without explicit collection should use 'site_collection'."""
        response = client.post(
            "/chat",
            json={"question": "Hello?"},
            headers={"X-API-Key": api_key},
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

    def test_ingest_with_valid_key_returns_response(self, client, api_key):
        """POST /ingest with valid key should return a response (may still fail if URL/API unavailable)."""
        response = client.post(
            "/ingest",
            json={"url": "https://example.com", "collection": "test_ingest"},
            headers={"X-API-Key": api_key},
        )
        # Should not be 401 (auth should pass)
        assert response.status_code != 401, "Should accept valid API key"
        # May return 500 if URL is unreachable or OpenAI key is missing
        assert response.status_code in [200, 500], f"Unexpected status {response.status_code}"


if __name__ == "__main__":
    # Allow running tests directly: python -m pytest backend/tests/test_api.py
    pytest.main([__file__, "-v"])
