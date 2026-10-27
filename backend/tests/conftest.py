"""Shared test bootstrap.

The env vars must be set BEFORE any test module imports app.* (the async
engine and the OpenAI client are built at import time).
"""
import asyncio
import os
import tempfile

os.environ["DATABASE_URL"] = (
    f"sqlite+aiosqlite:///{os.path.join(tempfile.mkdtemp(), 'test.db')}"
)
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    """Create DB tables once per session (TestClient does not run lifespan)."""
    from app.database import init_db

    asyncio.run(init_db())
