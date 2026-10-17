"""Jina AI embeddings (question + document chunk vectors)."""
import os

import requests

JINA_API_KEY = os.getenv("JINA_API_KEY")
JINA_EMBEDDING_URL = "https://api.jina.ai/v1/embeddings"
EMBED_MODEL = os.getenv("EMBED_MODEL", "jina-embeddings-v2-base-en")


def embed_texts(texts):
    """Embed texts using Jina AI API. Returns (embeddings, total_tokens).
    Set MOCK_EMBEDDINGS=true to use deterministic mock embeddings (saves API tokens during testing).
    """
    import numpy as np

    # --- Mock mode: deterministic embeddings from text hash (no API call) ---
    if os.getenv("MOCK_EMBEDDINGS", "false").lower() == "true":
        print("🤖 MOCK_EMBEDDINGS=true — using deterministic mock embeddings (no Jina API calls)")
        VECTOR_SIZE = 1536
        mock_vectors = []
        for t in texts:
            # Deterministic pseudo-random vector from text hash
            seed = hash(t) % (2**31)
            rng = np.random.RandomState(seed)
            vec = rng.randn(VECTOR_SIZE).astype(float).tolist()
            mock_vectors.append(vec)
        print(f"🎉 Mock-embedded {len(texts)} texts, vector size={VECTOR_SIZE}, total tokens=0")
        return mock_vectors, 0

    # --- Real Jina API mode ---
    if not JINA_API_KEY:
        raise Exception("JINA_API_KEY not set in environment variables")

    print(f"🔑 JINA_API_KEY starts with: {JINA_API_KEY[:10]}...")  # Debug log

    try:
        # Jina AI can handle batches, but let's keep it reasonable
        batch_size = 5  # Smaller batches for debugging
        all_embeddings = []
        total_jina_tokens = 0

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            print(f"📦 Processing batch {i//batch_size + 1} with {len(batch)} texts")

            response = requests.post(
                JINA_EMBEDDING_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {JINA_API_KEY}"
                },
                json={
                    "model": EMBED_MODEL,
                    "input": batch
                }
            )

            print(f"🌐 API Response status: {response.status_code}")

            if response.status_code != 200:
                print(f"❌ Jina API error: {response.status_code} - {response.text}")
                # Return empty embeddings for this batch
                all_embeddings.extend([[] for _ in batch])
                continue

            data = response.json()
            print(f"📊 API Response data keys: {list(data.keys())}")

            # Track Jina API tokens from usage
            if "usage" in data and "total_tokens" in data["usage"]:
                total_jina_tokens += data["usage"]["total_tokens"]

            if "data" not in data:
                print(f"❌ No 'data' in response: {data}")
                all_embeddings.extend([[] for _ in batch])
                continue

            embeddings = [item["embedding"] for item in data["data"]]
            print(f"✅ Got {len(embeddings)} embeddings, first vector length: {len(embeddings[0]) if embeddings else 0}")
            all_embeddings.extend(embeddings)

        print(f"🎉 Successfully embedded {len(texts)} texts using Jina AI, total vectors: {len(all_embeddings)}, total tokens: {total_jina_tokens}")
        return all_embeddings, total_jina_tokens

    except Exception as e:
        print(f"💥 Jina AI embedding failed: {e}")
        import traceback
        traceback.print_exc()
        # Return empty embeddings for all texts in case of failure
        return [[] for _ in texts], 0
