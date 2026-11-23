"""
Document bot (standalone service): manage collections and documents, answer
questions from them — the website RAG pipeline without site crawling.

Two modes in one chat, no mode switcher:
  * management — commands (/new, /collections, /use, /docs, /del, /add),
    a PDF/XLSX file sent to the chat, or a lone Google Docs/Sheets link;
  * Q&A — any other plain text is a question answered from the bound
    collection (embed -> Qdrant -> DeepSeek, streamed with live edits).

Runs as `python -m app.docbot` (no HTTP server) with long polling.
The polling/API plumbing is inherited from telegram_bot.TelegramBot.
"""
import asyncio
import logging
from typing import Any, Dict, Optional

from ..documents import (
    DOC_URL_RE,
    SHEET_URL_RE,
    DocumentError,
    delete_document_chunks,
    fetch_google_document,
    google_export_target,
    index_text,
    parse_pdf,
    parse_xlsx,
    validate_upload,
)
from ..embeddings import embed_texts
from ..rag import query_and_build_context
from ..telegram_bot import (
    API_BASE,
    BAD_PAYLOAD_TEXT,
    COLLECTION_NOT_FOUND_TEXT,
    ERROR_TEXT,
    LIMIT_TEXT,
    NOT_BOUND_TEXT,
    UNKNOWN_COMMAND_TEXT,
    TelegramBot,
    collection_exists,
    parse_command,
)
from . import collections as qcoll
from . import store

logger = logging.getLogger("docbot")

DOC_SYSTEM_PROMPT = "You are a helpful assistant answering questions about the user's documents."

HELP_TEXT = (
    "🤖 Документ-бот: база знаний из ваших документов.\n\n"
    "Управление:\n"
    "/new <имя> — создать коллекцию\n"
    "/collections — мои коллекции\n"
    "/use <имя> — переключить коллекцию\n"
    "/docs — список документов\n"
    "/del <номер> — удалить документ\n"
    "/add <ссылка> — добавить Google Doc/Sheet\n\n"
    "Документы: отправьте PDF или Excel файлом прямо в чат.\n"
    "Вопросы: просто напишите сообщение.\n\n"
    "Ссылка-приглашение:\nhttps://t.me/{bot}?start=collection_name"
)
WELCOME_TEXT = (
    "👋 Я — документ-бот: создаю базу знаний из ваших документов.\n\n"
    "1. Создайте коллекцию: /new имя_коллекции\n"
    "2. Отправьте PDF/Excel или ссылку на Google Doc/Sheet\n"
    "3. Задавайте вопросы — отвечу по документам\n\n"
    "Справка: /help"
)
BOUND_TEXT = (
    "✅ Чат подключён к коллекции «{collection}».\n"
    "Отправьте документ или задайте вопрос."
)
START_BOUND_TEXT = "✅ Вы подключены к коллекции «{collection}».\nЗадайте вопрос по документам."
NEW_SYNTAX_TEXT = "Используйте: /new имя_коллекции (буквы, цифры, «_» и «-»)"
NEW_CREATED_TEXT = (
    "✅ Коллекция «{collection}» создана и подключена к чату.\n"
    "Отправьте документ (PDF/Excel) или Google-ссылку."
)
EMPTY_COLLECTION_TEXT = (
    "📁 Коллекция «{collection}» пуста — отправьте PDF/Excel или "
    "Google-ссылку, и я добавлю документы."
)
PROCESSING_DOCS_TEXT = "⏳ Документы ещё обрабатываются — через минуту отвечу по ним."
EMPTY_DOCS_TEXT = "📁 Документов пока нет. Отправьте файл PDF/Excel или ссылку на Google Doc/Sheet."
ADD_SYNTAX_TEXT = (
    "Отправьте ссылку на Google Doc/Sheet отдельным сообщением "
    "или используйте: /add <ссылка>"
)
DEL_SYNTAX_TEXT = "Укажите номер документа из /docs, например: /del 3"
DEL_RANGE_TEXT = "Номер вне диапазона. Посмотрите список: /docs"
DOWNLOAD_FAILED_TEXT = "❌ Не удалось скачать файл из Telegram."


def _is_google_link_only(text: str) -> bool:
    """True when the whole message is a single Google Docs/Sheets URL."""
    if " " in text or "\n" in text:
        return False
    try:
        google_export_target(text)
        return True
    except DocumentError:
        return False


def _google_doc_name(url: str) -> str:
    """Human-usable name: the document id from the share URL."""
    match = DOC_URL_RE.search(url) or SHEET_URL_RE.search(url)
    return match.group(1) if match else url


class DocBot(TelegramBot):
    """Document Q&A bot: inherits polling/API/streaming from TelegramBot."""

    def __init__(self, token: str, **kwargs: Any):
        kwargs.setdefault("system_prompt", DOC_SYSTEM_PROMPT)
        super().__init__(token, **kwargs)

    # ------------------------------------------------------------- routing

    async def handle_update(self, update: Dict[str, Any]) -> None:
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return
        chat = msg.get("chat") or {}
        if chat.get("type") != "private":
            return  # private chats only
        chat_id = chat.get("id")
        if chat_id is None:
            return

        document = msg.get("document")
        if document:
            await self._handle_file(chat_id, document)
            return

        text = (msg.get("text") or "").strip()
        if not text:
            return  # stickers/media — ignore

        if text.startswith("/"):
            cmd, arg = parse_command(text)
            await self._dispatch(chat_id, cmd, arg, msg)
            return

        # A lone Google Docs/Sheets link means "add this document".
        if _is_google_link_only(text):
            await self._handle_google_link(chat_id, text)
            return

        await self._handle_question(chat_id, text)

    async def _dispatch(
        self, chat_id: int, cmd: str, arg: str, msg: Dict[str, Any]
    ) -> None:
        if cmd == "start":
            await self._cmd_start(chat_id, arg, msg)
        elif cmd == "help":
            await self._send_text(chat_id, self._help_text())
        elif cmd == "new":
            await self._cmd_new(chat_id, arg)
        elif cmd == "collections":
            await self._cmd_collections(chat_id)
        elif cmd == "use":
            await self._cmd_use(chat_id, arg)
        elif cmd == "docs":
            await self._cmd_docs(chat_id)
        elif cmd == "del":
            await self._cmd_del(chat_id, arg)
        elif cmd == "add":
            await self._handle_google_link(chat_id, arg)
        else:
            await self._send_text(chat_id, UNKNOWN_COMMAND_TEXT)

    def _help_text(self) -> str:
        return HELP_TEXT.format(bot=self._bot_username())

    def _spawn(self, coro) -> None:
        """Run a background coroutine without losing the reference."""
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    @staticmethod
    def _doc_status(doc) -> str:
        if doc.status == "completed":
            return f"✅ {doc.chunk_count} фрагм."
        if doc.status == "processing":
            return "⏳ обработка…"
        return f"❌ {(doc.error or 'ошибка')[:60]}"

    # --------------------------------------------------------------- binding

    async def _get_binding(self, chat_id: int, *args: Any, **kwargs: Any) -> Optional[str]:
        """Override: all docbot data access goes through the store layer."""
        return await store.get_binding(chat_id)

    # ----------------------------------------------------- management commands

    async def _cmd_start(self, chat_id: int, payload: str, msg: Dict[str, Any]) -> None:
        if not payload:
            binding = await store.get_binding(chat_id)
            if binding:
                await self._send_text(chat_id, START_BOUND_TEXT.format(collection=binding))
            else:
                await self._send_text(chat_id, WELCOME_TEXT)
            return
        if not qcoll.is_valid_name(payload):
            await self._send_text(chat_id, BAD_PAYLOAD_TEXT)
            return
        if not await asyncio.to_thread(collection_exists, payload):
            await self._send_text(
                chat_id, COLLECTION_NOT_FOUND_TEXT.format(collection=payload)
            )
            return
        await self._bind(chat_id, payload, msg)

    async def _bind(self, chat_id: int, collection: str, msg: Dict[str, Any]) -> None:
        username = (msg.get("from") or {}).get("username")
        await store.set_binding(chat_id, collection, username)
        await self._send_text(chat_id, BOUND_TEXT.format(collection=collection))

    async def _cmd_new(self, chat_id: int, arg: str) -> None:
        name = arg.strip()
        if not qcoll.is_valid_name(name):
            await self._send_text(chat_id, NEW_SYNTAX_TEXT)
            return
        try:
            await asyncio.to_thread(qcoll.create_collection, name)
        except qcoll.CollectionError as e:
            await self._send_text(chat_id, str(e))
            return
        except Exception as e:
            logger.exception("create_collection failed (%s)", name)
            await self._send_text(chat_id, f"❌ Не удалось создать коллекцию: {type(e).__name__}")
            return
        await store.add_collection(name, chat_id)
        await store.set_binding(chat_id, name)
        await self._send_text(chat_id, NEW_CREATED_TEXT.format(collection=name))

    async def _cmd_collections(self, chat_id: int) -> None:
        names = await store.list_collections()
        if not names:
            await self._send_text(chat_id, "📁 Коллекций пока нет. Создайте: /new имя_коллекции")
            return
        lines = "\n".join(f"• {name}" for name in names)
        await self._send_text(
            chat_id, f"📁 Ваши коллекции:\n{lines}\n\nПереключиться: /use <имя>"
        )

    async def _cmd_use(self, chat_id: int, arg: str) -> None:
        name = arg.strip()
        if not qcoll.is_valid_name(name):
            await self._send_text(chat_id, "Используйте: /use имя_коллекции")
            return
        if not await asyncio.to_thread(collection_exists, name):
            await self._send_text(chat_id, COLLECTION_NOT_FOUND_TEXT.format(collection=name))
            return
        await store.set_binding(chat_id, name)
        await self._send_text(chat_id, BOUND_TEXT.format(collection=name))

    async def _require_binding(self, chat_id: int) -> Optional[str]:
        collection = await store.get_binding(chat_id)
        if not collection:
            await self._send_text(chat_id, NOT_BOUND_TEXT.format(bot=self._bot_username()))
        return collection

    async def _cmd_docs(self, chat_id: int) -> None:
        collection = await self._require_binding(chat_id)
        if not collection:
            return
        docs = await store.list_documents(collection)
        if not docs:
            await self._send_text(chat_id, EMPTY_DOCS_TEXT)
            return
        lines = [
            f"{i}. {doc.name} — {self._doc_status(doc)}"
            for i, doc in enumerate(docs, start=1)
        ]
        await self._send_text(
            chat_id,
            f"📄 Документы «{collection}»:\n" + "\n".join(lines) + "\n\nУдалить: /del <номер>",
        )

    async def _cmd_del(self, chat_id: int, arg: str) -> None:
        collection = await self._require_binding(chat_id)
        if not collection:
            return
        try:
            num = int(arg.strip())
        except ValueError:
            await self._send_text(chat_id, DEL_SYNTAX_TEXT)
            return
        docs = await store.list_documents(collection)
        if not 1 <= num <= len(docs):
            await self._send_text(chat_id, DEL_RANGE_TEXT)
            return
        doc = docs[num - 1]
        removed = await asyncio.to_thread(delete_document_chunks, doc.id, collection)
        await store.delete_document(doc.id)
        await self._send_text(chat_id, f"🗑 Удалено «{doc.name}» ({removed} фрагментов)")


    # -------------------------------------------------------- document intake

    async def _handle_file(self, chat_id: int, document: Dict[str, Any]) -> None:
        collection = await self._require_binding(chat_id)
        if not collection:
            return

        file_name = document.get("file_name") or "document"
        file_size = int(document.get("file_size") or 0)
        try:
            source_type = validate_upload(file_name, file_size)
        except DocumentError as e:
            await self._send_text(chat_id, str(e))
            return

        # Download via getFile (URL contains the token — never log it).
        try:
            info = await self.api("getFile", file_id=document["file_id"])
            file_url = f"{API_BASE}/file/bot{self.token}/{info['file_path']}"
            resp = await self.client.get(file_url, timeout=120)
            resp.raise_for_status()
            data = resp.content
        except Exception as e:
            logger.error("file download failed (chat=%s): %s", chat_id, type(e).__name__)
            await self._send_text(chat_id, DOWNLOAD_FAILED_TEXT)
            return

        try:
            validate_upload(file_name, len(data))  # authoritative size check
        except DocumentError as e:
            await self._send_text(chat_id, str(e))
            return

        doc_id = await store.add_document(
            collection, file_name, source_type, file_name=file_name
        )
        reply_id = await self._send_text(chat_id, f"⏳ Обрабатываю «{file_name}»…")
        self._spawn(
            self._ingest_background(
                doc_id, collection, file_bytes=data, chat_id=chat_id, message_id=reply_id
            )
        )

    async def _handle_google_link(self, chat_id: int, url: str) -> None:
        url = url.strip()
        if not url:
            await self._send_text(chat_id, ADD_SYNTAX_TEXT)
            return
        collection = await self._require_binding(chat_id)
        if not collection:
            return
        try:
            source_type, _ = google_export_target(url)  # classify / fail fast
        except DocumentError as e:
            await self._send_text(chat_id, str(e))
            return

        name = _google_doc_name(url)
        doc_id = await store.add_document(
            collection, name, source_type, source_url=url
        )
        reply_id = await self._send_text(chat_id, f"⏳ Добавляю «{name}»…")
        self._spawn(
            self._ingest_background(
                doc_id, collection, google_url=url, chat_id=chat_id, message_id=reply_id
            )
        )


    # -------------------------------------------------- background ingestion

    async def _ingest_background(
        self,
        doc_id: int,
        collection: str,
        *,
        file_bytes: Optional[bytes] = None,
        google_url: Optional[str] = None,
        chat_id: Optional[int] = None,
        message_id: Optional[int] = None,
    ) -> None:
        """Parse (in a thread), index into Qdrant, update DB, edit the reply."""
        doc = await store.get_document(doc_id)
        name = doc.name if doc else str(doc_id)
        source_type = doc.source_type if doc else "pdf"
        try:
            if google_url:
                text = await asyncio.to_thread(fetch_google_document, google_url)
            else:
                if not doc:
                    raise DocumentError("Документ не найден")
                parser = parse_pdf if doc.source_type == "pdf" else parse_xlsx
                text = await asyncio.to_thread(parser, file_bytes or b"")

            chunk_count = await asyncio.to_thread(
                index_text, text, collection, doc_id, source_type, name
            )
            await store.update_document(doc_id, status="completed", chunk_count=chunk_count)
            if chat_id and message_id:
                await self._edit_text(
                    chat_id, message_id, f"✅ «{name}»: {chunk_count} фрагментов добавлено"
                )
            logger.info("document %s indexed: %s chunks", doc_id, chunk_count)
        except DocumentError as e:
            await self._mark_failed(doc_id, chat_id, message_id, name, str(e))
        except Exception as e:
            logger.exception("document ingest failed (%s)", doc_id)
            await self._mark_failed(
                doc_id, chat_id, message_id, name, f"внутренняя ошибка ({type(e).__name__})"
            )

    async def _mark_failed(
        self,
        doc_id: int,
        chat_id: Optional[int],
        message_id: Optional[int],
        name: str,
        error: str,
    ) -> None:
        await store.update_document(doc_id, status="failed", error=error[:500])
        if chat_id and message_id:
            await self._edit_text(chat_id, message_id, f"❌ «{name}»: {error}")
        logger.warning("document %s failed: %s", doc_id, error)

    # --------------------------------------------------------------- answers

    async def _answer(self, chat_id: int, question: str, collection: str) -> None:
        """RAG answer from documents only (no site/usage logic)."""
        points = await asyncio.to_thread(qcoll.collection_points, collection)
        if points is None:
            await self._send_text(
                chat_id, COLLECTION_NOT_FOUND_TEXT.format(collection=collection)
            )
            return
        if points == 0:
            docs = await store.list_documents(collection)
            if any(d.status == "processing" for d in docs):
                await self._send_text(chat_id, PROCESSING_DOCS_TEXT)
            else:
                await self._send_text(
                    chat_id, EMPTY_COLLECTION_TEXT.format(collection=collection)
                )
            return

        # 1) embed question (embed_texts returns (embeddings, jina_tokens) tuple)
        try:
            embs_result = await asyncio.to_thread(embed_texts, [question])
        except Exception:
            logger.exception("embed_texts failed (chat=%s)", chat_id)
            await self._send_text(chat_id, ERROR_TEXT)
            return
        embs, _ = embs_result if isinstance(embs_result, tuple) else (embs_result, 0)
        if not embs or not embs[0]:
            await self._send_text(chat_id, ERROR_TEXT)
            return

        # 2) query qdrant
        snippets = await asyncio.to_thread(
            query_and_build_context, embs[0], collection_name=collection
        )

        # 3) stream the answer — streaming/typing/edits inherited from TelegramBot
        await self._stream_answer(chat_id, question, snippets, None, 0)

