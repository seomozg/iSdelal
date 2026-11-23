"""
Unit tests for the document bot (long-polling bot, no network access).
Run with: pytest backend/tests/test_docbot.py -v
"""
import asyncio
import json

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.docbot import store
from app.docbot.bot import DocBot
from app.docbot.models import DocbotCollection, DocbotDocument
from tests.test_documents import minimal_pdf

import app.models  # noqa: F401  — register shared tables (TelegramChat)

# What the mock Telegram file endpoint serves by default (matches file_update names).
PDF_BYTES = minimal_pdf("contract price delivery terms and contact details here")


def text_update(text: str, chat_id: int = 111) -> dict:
    return {
        "update_id": 1,
        "message": {
            "message_id": 10,
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": chat_id, "username": "tester"},
            "text": text,
        },
    }


def file_update(
    file_name: str, file_size: int = 100, file_id: str = "fid123", chat_id: int = 111
) -> dict:
    return {
        "update_id": 2,
        "message": {
            "message_id": 11,
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": chat_id, "username": "tester"},
            "document": {"file_id": file_id, "file_name": file_name, "file_size": file_size},
        },
    }


def make_handler(calls: list, file_bytes: bytes = b""):
    """Mock Bot API transport: records calls, serves getFile downloads."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "/file/bot" in path:
            calls.append(("file_download", path))
            return httpx.Response(200, content=file_bytes)
        method = path.rsplit("/", 1)[-1]
        payload = json.loads(request.content) if request.content else {}
        calls.append((method, payload))
        if method == "getMe":
            return httpx.Response(200, json={"ok": True, "result": {"username": "doc_test_bot"}})
        if method == "getFile":
            return httpx.Response(
                200, json={"ok": True, "result": {"file_path": "documents/test.pdf"}}
            )
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})

    return handler


def sent_texts(calls: list) -> list:
    return [p.get("text", "") for m, p in calls if m in ("sendMessage", "editMessageText")]


@pytest_asyncio.fixture
async def db(tmp_path, monkeypatch):
    """Isolated SQLite for one test: also redirects the docbot store to it."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/docbot.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr("app.docbot.store.async_session_factory", factory)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def bot(db):
    """DocBot with a mocked Telegram API; returns (bot, recorded_calls)."""
    calls: list = []
    client = httpx.AsyncClient(transport=httpx.MockTransport(make_handler(calls, PDF_BYTES)))
    instance = DocBot("TEST_TOKEN", session_factory=db, http=client, daily_limit=50)
    instance.username = "doc_test_bot"  # normally set by run() after getMe
    return instance, calls


@pytest.fixture
def rag_mocks(monkeypatch):
    """Deterministic fakes for the answer pipeline (embed/search/LLM)."""
    state = {"embed": 0, "search": 0, "stream": 0}

    def fake_embed(texts):
        state["embed"] += 1
        return ([[0.1] * 8], 3)

    def fake_search(query_embedding, collection_name=""):
        state["search"] += 1
        return [{"text": "Из документа: стоимость аренды корта 3000 рублей", "url": "doc", "score": 0.9}]

    def fake_stream(question, snippets, usage=None, system_prompt=None):
        state["stream"] += 1
        if usage is not None:
            usage["total_tokens"] = 11
        yield "Ответ "
        yield "из документа"

    monkeypatch.setattr("app.docbot.bot.embed_texts", fake_embed)
    monkeypatch.setattr("app.docbot.bot.query_and_build_context", fake_search)
    monkeypatch.setattr("app.telegram_bot.call_llm_stream", fake_stream)
    return state


class TestRouting:
    """Message routing: files, lone Google links, questions, limits."""

    @pytest.mark.asyncio
    async def test_unbound_question_prompts_binding(self, bot):
        b, calls = bot
        await b.handle_update(text_update("что в документах?"))
        assert any("не подключён" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_bound_question_streams_answer(self, bot, rag_mocks, monkeypatch):
        b, calls = bot
        await store.set_binding(111, "col_docs")
        monkeypatch.setattr("app.docbot.bot.qcoll.collection_points", lambda name: 5)

        await b.handle_update(text_update("сколько стоит аренда?"))

        assert rag_mocks["embed"] == 1
        assert rag_mocks["search"] == 1
        assert rag_mocks["stream"] == 1
        assert any("Ответ из документа" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_question_on_empty_collection(self, bot, monkeypatch):
        b, calls = bot
        await store.set_binding(111, "col_empty")
        monkeypatch.setattr("app.docbot.bot.qcoll.collection_points", lambda name: 0)

        await b.handle_update(text_update("вопрос"))
        assert any("пуста" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_question_while_documents_processing(self, bot, monkeypatch):
        b, calls = bot
        await store.set_binding(111, "col_busy")
        monkeypatch.setattr("app.docbot.bot.qcoll.collection_points", lambda name: 0)
        await store.add_document("col_busy", "a.pdf", "pdf")

        await b.handle_update(text_update("вопрос"))
        assert any("обрабатываются" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_lone_google_link_adds_document(self, bot, monkeypatch):
        b, calls = bot
        await store.set_binding(111, "col_docs")
        bg = []

        async def fake_bg(self, doc_id, collection, **kw):
            bg.append((doc_id, collection, kw))

        monkeypatch.setattr(DocBot, "_ingest_background", fake_bg)
        url = "https://docs.google.com/document/d/abc123XYZ/edit"
        await b.handle_update(text_update(url))

        docs = await store.list_documents("col_docs")
        assert len(docs) == 1
        assert docs[0].source_type == "google_doc"
        assert docs[0].name == "abc123XYZ"
        await asyncio.sleep(0)
        assert bg and bg[0][1] == "col_docs"
        assert any("⏳" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_link_inside_question_is_a_question(self, bot, monkeypatch):
        """A Google URL with surrounding text is a question, not an add."""
        b, calls = bot
        monkeypatch.setattr("app.docbot.bot.qcoll.collection_points", lambda name: 5)
        url = "https://docs.google.com/document/d/abc/edit"
        await b.handle_update(text_update(f"что написано тут {url}?"))
        # no binding -> prompts instead of adding
        assert any("не подключён" in t for t in sent_texts(calls))
        assert await store.list_documents("col_docs") == []

    @pytest.mark.asyncio
    async def test_file_upload_creates_document(self, bot, monkeypatch):
        b, calls = bot
        await store.set_binding(111, "col_docs")
        bg = []

        async def fake_bg(self, doc_id, collection, **kw):
            bg.append((doc_id, collection, kw.get("file_bytes")))

        monkeypatch.setattr(DocBot, "_ingest_background", fake_bg)
        pdf = PDF_BYTES
        await b.handle_update(file_update("contract.pdf", file_size=len(pdf)))
        # the handler must actually download the file through the mock transport
        downloads = [m for m, _ in calls if m == "file_download"]
        assert downloads, "file was not downloaded via getFile"
        docs = await store.list_documents("col_docs")
        assert docs[0].status == "processing"
        assert docs[0].source_type == "pdf"
        await asyncio.sleep(0)
        assert bg and bg[0][2] == pdf

    @pytest.mark.asyncio
    async def test_unsupported_file_rejected(self, bot):
        b, calls = bot
        await store.set_binding(111, "col_docs")
        await b.handle_update(file_update("notes.txt"))
        assert any("Поддерживаются только файлы" in t for t in sent_texts(calls))
        assert await store.list_documents("col_docs") == []

    @pytest.mark.asyncio
    async def test_daily_limit(self, bot):
        b, calls = bot
        b.limiter.limit = 1
        await store.set_binding(111, "col_docs")
        await b.handle_update(text_update("вопрос 1"))
        await b.handle_update(text_update("вопрос 2"))
        assert any("лимит" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_typing_shows_while_thinking(self, bot, rag_mocks, monkeypatch):
        """«Печатает» видно с момента вопроса: пока идут поиск по документам и LLM."""
        import time as _time

        b, calls = bot
        await store.set_binding(111, "col_docs")
        monkeypatch.setattr("app.docbot.bot.qcoll.collection_points", lambda name: 5)

        seen = {}

        def slow_embed(texts):
            _time.sleep(0.05)  # время, чтобы typing-задача отработала в loop
            seen["typing_during_embed"] = any(m == "sendChatAction" for m, _ in calls)
            return ([[0.1] * 8], 3)

        monkeypatch.setattr("app.docbot.bot.embed_texts", slow_embed)

        await b.handle_update(text_update("сколько стоит аренда?"))

        assert seen.get("typing_during_embed") is True
        assert b._typing_tasks == {}  # индикатор погашен после ответа
        assert any("Ответ из документа" in t for t in sent_texts(calls))



class TestCommands:
    """Management commands: /new, /collections, /use, /start, /docs, /del."""

    @pytest.mark.asyncio
    async def test_new_creates_and_binds(self, bot, monkeypatch):
        from app.docbot.collections import CollectionError  # noqa: F401 (doc)

        b, calls = bot
        monkeypatch.setattr("app.docbot.bot.qcoll.create_collection", lambda name: None)

        await b.handle_update(text_update("/new my_docs"))

        assert await store.get_binding(111) == "my_docs"
        assert await store.list_collections() == ["my_docs"]
        assert any("✅ Коллекция «my_docs» создана" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_new_rejects_invalid_name(self, bot, monkeypatch):
        b, calls = bot
        monkeypatch.setattr("app.docbot.bot.qcoll.create_collection", lambda name: None)

        await b.handle_update(text_update("/new bad name"))

        assert await store.get_binding(111) is None
        assert any("Используйте: /new" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_new_duplicate_reports_error(self, bot, monkeypatch):
        from app.docbot.collections import CollectionError

        b, calls = bot

        def dup(name):
            raise CollectionError(f"Коллекция «{name}» уже существует")

        monkeypatch.setattr("app.docbot.bot.qcoll.create_collection", dup)

        await b.handle_update(text_update("/new my_docs"))

        assert any("уже существует" in t for t in sent_texts(calls))
        assert await store.list_collections() == []

    @pytest.mark.asyncio
    async def test_collections_empty_and_listed(self, bot):
        b, calls = bot
        await b.handle_update(text_update("/collections"))
        assert any("пока нет" in t for t in sent_texts(calls))

        await store.add_collection("alpha", 111)
        await store.add_collection("beta", 111)
        await b.handle_update(text_update("/collections"))
        texts = sent_texts(calls)
        assert any("• alpha" in t and "• beta" in t for t in texts)

    @pytest.mark.asyncio
    async def test_use_binds_existing_collection(self, bot, monkeypatch):
        b, calls = bot
        monkeypatch.setattr("app.docbot.bot.collection_exists", lambda name: name == "col2")

        await b.handle_update(text_update("/use col2"))
        assert await store.get_binding(111) == "col2"
        assert any("подключён к коллекции «col2»" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_use_unknown_collection(self, bot, monkeypatch):
        b, calls = bot
        monkeypatch.setattr("app.docbot.bot.collection_exists", lambda name: False)

        await b.handle_update(text_update("/use ghost"))
        assert await store.get_binding(111) is None
        assert any("не найдена" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_start_payload_binds(self, bot, monkeypatch):
        b, calls = bot
        monkeypatch.setattr("app.docbot.bot.collection_exists", lambda name: name == "col_x")

        await b.handle_update(text_update("/start col_x"))
        assert await store.get_binding(111) == "col_x"

    @pytest.mark.asyncio
    async def test_start_invalid_payload(self, bot):
        b, calls = bot
        await b.handle_update(text_update("/start bad name"))
        assert await store.get_binding(111) is None
        assert any("Некорректный" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_start_unknown_collection(self, bot, monkeypatch):
        b, calls = bot
        monkeypatch.setattr("app.docbot.bot.collection_exists", lambda name: False)

        await b.handle_update(text_update("/start ghost"))
        assert await store.get_binding(111) is None
        assert any("не найдена" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_docs_requires_binding(self, bot):
        b, calls = bot
        await b.handle_update(text_update("/docs"))
        assert any("не подключён" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_docs_lists_documents(self, bot):
        b, calls = bot
        await store.set_binding(111, "col_docs")
        await store.add_document("col_docs", "prices.pdf", "pdf", status="completed")
        await store.add_document("col_docs", "sheet1", "google_sheet", status="failed")

        await b.handle_update(text_update("/docs"))

        listing = next(t for t in sent_texts(calls) if "1. prices.pdf" in t)
        assert "✅" in listing
        assert "2. sheet1" in listing
        assert "❌" in listing

    @pytest.mark.asyncio
    async def test_del_removes_document(self, bot, monkeypatch):
        b, calls = bot
        await store.set_binding(111, "col_docs")
        doc_id = await store.add_document("col_docs", "old.pdf", "pdf")
        monkeypatch.setattr("app.docbot.bot.delete_document_chunks", lambda d, c: 7)

        await b.handle_update(text_update("/del 1"))

        assert await store.list_documents("col_docs") == []
        assert any("🗑 Удалено «old.pdf» (7 фрагментов)" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_del_out_of_range(self, bot):
        b, calls = bot
        await store.set_binding(111, "col_docs")
        await b.handle_update(text_update("/del 5"))
        assert any("вне диапазона" in t for t in sent_texts(calls))

    @pytest.mark.asyncio
    async def test_help_lists_commands(self, bot):
        b, calls = bot
        await b.handle_update(text_update("/help"))
        help_msg = next(t for t in sent_texts(calls) if "/new <имя>" in t)
        assert "/docs" in help_msg
        assert "doc_test_bot" in help_msg  # username from mocked getMe

