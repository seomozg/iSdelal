"""
Unit tests for the Telegram bot (no network access required).
Run with: pytest backend/tests/test_telegram_bot.py -v
Or inside container: docker compose exec backend pytest tests/test_telegram_bot.py -v
"""

from datetime import date

import httpx
import pytest

from app.telegram_bot import (
    DailyLimiter,
    TelegramBot,
    is_valid_collection_name,
    parse_command,
    split_message,
)


# ------------------------------------------------------------------ helpers

def make_update(text: str, chat_id: int = 111, chat_type: str = "private"):
    return {
        "update_id": 1,
        "message": {
            "message_id": 10,
            "chat": {"id": chat_id, "type": chat_type},
            "from": {"id": chat_id, "username": "tester"},
            "text": text,
        },
    }


def make_bot(calls: list, daily_limit: int = 50) -> TelegramBot:
    """Bot with mocked Bot API transport (records outgoing calls)."""

    def handler(request: httpx.Request) -> httpx.Response:
        method = request.url.path.rsplit("/", 1)[-1]
        body = request.content
        payload = __import__("json").loads(body) if body else {}
        calls.append((method, payload))
        if method == "getMe":
            return httpx.Response(200, json={"ok": True, "result": {"username": "test_bot"}})
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TelegramBot("TEST_TOKEN", daily_limit=daily_limit, http=client)


def sent_texts(calls: list) -> list:
    return [p.get("text", "") for m, p in calls if m == "sendMessage"]


# ------------------------------------------------------------------ tests

class TestPayloadParsing:
    def test_valid_collection(self):
        assert is_valid_collection_name("padel_russia_online")
        assert is_valid_collection_name("a")
        assert is_valid_collection_name("A-b_c-9")

    def test_invalid_collection(self):
        assert not is_valid_collection_name("")
        assert not is_valid_collection_name("with space")
        assert not is_valid_collection_name("bad!chars")
        assert not is_valid_collection_name("x" * 65)

    def test_parse_command_simple(self):
        assert parse_command("/start padel_russia_online") == ("start", "padel_russia_online")

    def test_parse_command_with_bot_suffix(self):
        assert parse_command("/collection@my_bot  some_name") == ("collection", "some_name")

    def test_parse_command_no_args(self):
        assert parse_command("/help") == ("help", "")


class TestSplitMessage:
    def test_short_text_single_part(self):
        assert split_message("hello") == ["hello"]

    def test_empty_text(self):
        assert split_message("") == []

    def test_long_text_split_into_parts(self):
        text = ("word " * 5000).strip()
        parts = split_message(text, limit=100)
        assert all(len(p) <= 100 for p in parts)
        assert " ".join(parts).split() == text.split()  # content preserved

    def test_prefers_line_breaks(self):
        text = "line1\nline2\n" + "x" * 200
        parts = split_message(text, limit=10)
        assert parts[0] == "line1\nline2" or parts[0].startswith("line1")


class TestDailyLimiter:
    def test_allows_up_to_limit(self):
        limiter = DailyLimiter(limit=3)
        today = date(2026, 1, 1)
        assert all(limiter.allow(1, today=today) for _ in range(3))
        assert not limiter.allow(1, today=today)

    def test_independent_chats(self):
        limiter = DailyLimiter(limit=1)
        today = date(2026, 1, 1)
        assert limiter.allow(1, today=today)
        assert limiter.allow(2, today=today)
        assert not limiter.allow(1, today=today)

    def test_resets_next_day(self):
        limiter = DailyLimiter(limit=1)
        assert limiter.allow(1, today=date(2026, 1, 1))
        assert not limiter.allow(1, today=date(2026, 1, 1))
        assert limiter.allow(1, today=date(2026, 1, 2))

    def test_disabled_when_zero(self):
        limiter = DailyLimiter(limit=0)
        assert all(limiter.allow(1) for _ in range(100))


# ----------------------------------------------------------- async routing

import pytest_asyncio


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.database import Base
    import app.models  # noqa: F401  — register tables

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test_tg.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture
def rag_mocks(monkeypatch):
    """Replace the whole RAG pipeline with deterministic fakes."""
    import app.telegram_bot as tb

    state = {"embed_calls": 0, "search_calls": 0, "stream_calls": 0, "collections": []}

    def fake_embed(texts):
        state["embed_calls"] += 1
        return ([[0.1] * 8], 3)

    def fake_search(query_embedding, collection_name=""):
        state["search_calls"] += 1
        return [{"text": "Падел-корты России: 28 кортов в Москве", "url": "https://x", "score": 0.9}]

    def fake_stream(question, snippets, usage=None):
        state["stream_calls"] += 1
        if usage is not None:
            usage["total_tokens"] = 17
        yield "Ответ "
        yield "из "
        yield "контекста"

    def fake_collection_exists(name):
        state["collections"].append(name)
        return name == "padel_russia_online"

    monkeypatch.setattr(tb, "embed_texts", fake_embed)
    monkeypatch.setattr(tb, "query_and_build_context", fake_search)
    monkeypatch.setattr(tb, "call_llm_stream", fake_stream)
    monkeypatch.setattr(tb, "collection_exists", fake_collection_exists)
    monkeypatch.setattr(tb, "_get_collection_active_ingests", lambda c: [])
    return state


class TestRouting:
    @pytest.mark.asyncio
    async def test_group_message_ignored(self, session_factory):
        calls = []
        bot = make_bot(calls)
        bot.session_factory = session_factory
        await bot.handle_update(make_update("привет", chat_type="supergroup"))
        assert calls == []

    @pytest.mark.asyncio
    async def test_non_text_message_ignored(self, session_factory):
        calls = []
        bot = make_bot(calls)
        bot.session_factory = session_factory
        update = make_update("")
        update["message"].pop("text")
        await bot.handle_update(update)
        assert calls == []

    @pytest.mark.asyncio
    async def test_unknown_command(self, session_factory):
        calls = []
        bot = make_bot(calls)
        bot.session_factory = session_factory
        await bot.handle_update(make_update("/foo"))
        assert any("Неизвестная команда" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_question_without_binding_prompts_link(self, session_factory):
        calls = []
        bot = make_bot(calls)
        bot.session_factory = session_factory
        await bot.handle_update(make_update("сколько кортов?"))
        assert any("не подключён" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_daily_limit_blocks_question(self, session_factory, rag_mocks):
        calls = []
        bot = make_bot(calls, daily_limit=1)
        bot.session_factory = session_factory
        await bot._set_binding(111, "padel_russia_online", "tester")
        await bot.handle_update(make_update("вопрос 1"))
        await bot.handle_update(make_update("вопрос 2"))
        texts = sent_texts(calls)
        assert any("лимит" in t for t in texts)
        assert rag_mocks["stream_calls"] == 1


class TestBinding:
    @pytest.mark.asyncio
    async def test_start_binds_collection(self, session_factory, rag_mocks):
        calls = []
        bot = make_bot(calls)
        bot.session_factory = session_factory
        await bot.handle_update(make_update("/start padel_russia_online"))
        assert await bot._get_binding(111) == "padel_russia_online"
        assert any("✅" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_start_unknown_collection_not_bound(self, session_factory, rag_mocks):
        calls = []
        bot = make_bot(calls)
        bot.session_factory = session_factory
        await bot.handle_update(make_update("/start no_such_collection"))
        assert await bot._get_binding(111) is None
        assert any("не найдена" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_start_without_payload_when_bound(self, session_factory, rag_mocks):
        calls = []
        bot = make_bot(calls)
        bot.session_factory = session_factory
        await bot._set_binding(111, "padel_russia_online", None)
        await bot.handle_update(make_update("/start"))
        assert any("уже подключены" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_collection_switch(self, session_factory, rag_mocks):
        calls = []
        bot = make_bot(calls)
        bot.session_factory = session_factory
        await bot.handle_update(make_update("/collection padel_russia_online"))
        assert await bot._get_binding(111) == "padel_russia_online"

    @pytest.mark.asyncio
    async def test_binding_persists_across_bot_instances(self, session_factory, rag_mocks):
        bot1 = make_bot([])
        bot1.session_factory = session_factory
        await bot1._set_binding(555, "padel_russia_online", "someone")
        bot2 = make_bot([])
        bot2.session_factory = session_factory
        assert await bot2._get_binding(555) == "padel_russia_online"


class TestAnswerFlow:
    @pytest.mark.asyncio
    async def test_answer_streams_llm_tokens_with_context(self, session_factory, rag_mocks):
        calls = []
        bot = make_bot(calls)
        bot.session_factory = session_factory
        await bot._set_binding(111, "padel_russia_online", None)
        await bot.handle_update(make_update("есть ли корты в Москве?"))
        assert rag_mocks["embed_calls"] == 1
        assert rag_mocks["search_calls"] == 1
        assert rag_mocks["stream_calls"] == 1
        edits = [p["text"] for m, p in calls if m == "editMessageText"]
        final_texts = edits + sent_texts(calls)
        assert any("Ответ из контекста" in t for t in final_texts)

    @pytest.mark.asyncio
    async def test_answer_sends_typing_action(self, session_factory, rag_mocks):
        calls = []
        bot = make_bot(calls)
        bot.session_factory = session_factory
        await bot._set_binding(111, "padel_russia_online", None)
        await bot.handle_update(make_update("вопрос"))
        assert any(m == "sendChatAction" for m, _ in calls)

    @pytest.mark.asyncio
    async def test_llm_failure_sends_error_message(self, session_factory, rag_mocks, monkeypatch):
        import app.telegram_bot as tb

        def broken_stream(question, snippets, usage=None):
            raise RuntimeError("llm down")
            yield  # pragma: no cover

        monkeypatch.setattr(tb, "call_llm_stream", broken_stream)
        calls = []
        bot = make_bot(calls)
        bot.session_factory = session_factory
        await bot._set_binding(111, "padel_russia_online", None)
        await bot.handle_update(make_update("вопрос"))
        assert any("⚠️" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_active_ingest_short_circuits(self, session_factory, rag_mocks, monkeypatch):
        import app.telegram_bot as tb

        monkeypatch.setattr(tb, "_get_collection_active_ingests", lambda c: [{"job_id": "j1"}])
        calls = []
        bot = make_bot(calls)
        bot.session_factory = session_factory
        await bot._set_binding(111, "padel_russia_online", None)
        await bot.handle_update(make_update("вопрос"))
        assert any("индексирует" in t for t in sent_texts(calls))
        assert rag_mocks["embed_calls"] == 0

