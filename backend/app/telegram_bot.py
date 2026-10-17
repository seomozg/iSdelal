"""
Telegram bot that answers questions from a Qdrant collection (RAG),
mirroring the website chat widget behaviour.

Runs as a background asyncio task inside the FastAPI app (single uvicorn worker),
using Bot API long polling (getUpdates). Requires TG_BOT_TOKEN env var.

Deep link for binding a chat to a collection:
    https://t.me/<bot_username>?start=<collection_name>
(Telegram only supports the `start` parameter, arbitrary query params like
?collection= are ignored.)
"""

import asyncio
import logging
import os
import re
import time
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import select

from .database import async_session_factory
from .embeddings import embed_texts
from .jobs import _get_collection_active_ingests
from .models import Site, TelegramChat
from .qdrant_client import get_qdrant_client
from .rag import call_llm_stream, query_and_build_context
from .tracking import record_deepseek_usage, record_jina_usage

logger = logging.getLogger("telegram_bot")

API_BASE = "https://api.telegram.org"
MESSAGE_LIMIT = 4096  # Telegram max message length
EDIT_INTERVAL = 1.0   # min seconds between message edits while streaming
TYPING_INTERVAL = 4.5  # sendChatAction is valid ~5s

COLLECTION_PAYLOAD_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

HELP_TEXT = (
    "🤖 Я отвечаю на вопросы по контенту сайта — так же, как виджет на сайте.\n\n"
    "Команды:\n"
    "/start <коллекция> — подключить бота к базе знаний\n"
    "/collection <коллекция> — переключить базу знаний\n"
    "/help — показать эту справку\n\n"
    "Ссылка-приглашение:\nhttps://t.me/{bot}?start=collection_name"
)
START_BOUND_TEXT = (
    "✅ Готово! Бот подключён к базе знаний «{collection}».\n"
    "Задайте вопрос — отвечу на основе контента сайта."
)
START_NO_PAYLOAD_BOUND_TEXT = (
    "👋 Вы уже подключены к базе знаний «{collection}».\nПросто напишите вопрос."
)
START_NO_PAYLOAD_TEXT = (
    "👋 Бот пока не подключён к базе знаний.\n\n"
    "Откройте бота по ссылке:\nhttps://t.me/{bot}?start=ваша_коллекция\n\n"
    "Или посмотрите /help."
)
COLLECTION_NOT_FOUND_TEXT = (
    "❌ База знаний «{collection}» не найдена. Проверьте ссылку или /help."
)
NOT_BOUND_TEXT = (
    "👋 Бот не подключён к базе знаний.\n\n"
    "Откройте бота по ссылке:\nhttps://t.me/{bot}?start=ваша_коллекция"
)
LIMIT_TEXT = "⏳ Дневной лимит сообщений исчерпан. Попробуйте позже."
PROCESSING_TEXT = (
    "🕒 AI всё ещё индексирует этот сайт. Пожалуйста, подождите пару минут и попробуйте снова."
)
ERROR_TEXT = "⚠️ Не удалось получить ответ. Попробуйте позже."
BAD_PAYLOAD_TEXT = "❌ Некорректный параметр подключения. Проверьте ссылку."
UNKNOWN_COMMAND_TEXT = "Неизвестная команда. Наберите /help."
BAD_COLLECTION_SYNTAX_TEXT = "Укажите базу знаний: /collection имя_коллекции"

_SENTINEL = object()


class TelegramAPIError(Exception):
    """Bot API returned ok=false."""

    def __init__(self, method: str, description: str):
        super().__init__(f"{method}: {description}")
        self.method = method
        self.description = description


def parse_command(text: str) -> Tuple[str, str]:
    """Split '/cmd@bot arg...' into ('cmd', 'arg...')."""
    head, _, arg = text.partition(" ")
    cmd = head[1:].split("@", 1)[0].lower()
    return cmd, arg.strip()


def is_valid_collection_name(name: str) -> bool:
    """Telegram start payload: 1-64 chars of [A-Za-z0-9_-]."""
    return bool(COLLECTION_PAYLOAD_RE.fullmatch(name))


def split_message(text: str, limit: int = MESSAGE_LIMIT) -> List[str]:
    """Split text into parts <= limit, preferring line/word boundaries."""
    if len(text) <= limit:
        return [text] if text else []
    parts: List[str] = []
    rest = text
    while rest:
        if len(rest) <= limit:
            parts.append(rest)
            break
        cut = rest.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = rest.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(rest[:cut])
        rest = rest[cut:]
    return parts


class DailyLimiter:
    """Per-chat daily message counter (in-memory, resets on day change)."""

    def __init__(self, limit: int):
        self.limit = limit
        self._counts: Dict[int, Tuple[date, int]] = {}

    def allow(self, chat_id: int, today: Optional[date] = None) -> bool:
        if self.limit <= 0:
            return True
        today = today or date.today()
        day, count = self._counts.get(chat_id, (today, 0))
        if day != today:
            day, count = today, 0
        if count >= self.limit:
            self._counts[chat_id] = (day, count)
            if len(self._counts) > 4096:  # prune stale entries
                self._counts = {k: v for k, v in self._counts.items() if v[0] == today}
            return False
        self._counts[chat_id] = (day, count + 1)
        return True


def collection_exists(name: str) -> bool:
    """Check that a Qdrant collection exists (sync; run in a thread)."""
    try:
        get_qdrant_client().get_collection(name)
        return True
    except Exception:
        return False


class TelegramBot:
    def __init__(
        self,
        token: str,
        *,
        daily_limit: Optional[int] = None,
        session_factory: Optional[Callable[..., Any]] = None,
        http: Optional[httpx.AsyncClient] = None,
        poll_timeout: int = 50,
    ):
        self.token = token
        self.api_root = f"{API_BASE}/bot{token}"
        self.session_factory = session_factory or async_session_factory
        self.client = http or httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
        self._owns_client = http is None
        self.poll_timeout = poll_timeout
        if daily_limit is None:
            daily_limit = int(os.getenv("TG_DAILY_LIMIT", "50"))
        self.limiter = DailyLimiter(daily_limit)
        self.offset: Optional[int] = None
        self.username: Optional[str] = None
        self._running = False
        self._tasks: set = set()
        self._answer_sem = asyncio.Semaphore(int(os.getenv("TG_MAX_CONCURRENT", "4")))

    # ------------------------------------------------------------------ API

    async def api(self, method: str, **payload) -> Any:
        resp = await self.client.post(f"{self.api_root}/{method}", json=payload)
        try:
            data = resp.json()
        except ValueError:
            raise TelegramAPIError(method, f"non-JSON response (HTTP {resp.status_code})")
        if not data.get("ok"):
            raise TelegramAPIError(method, data.get("description", f"HTTP {resp.status_code}"))
        return data.get("result")

    async def _send_text(self, chat_id: int, text: str) -> Optional[int]:
        if not text:
            return None
        try:
            result = await self.api("sendMessage", chat_id=chat_id, text=text)
            return result.get("message_id") if isinstance(result, dict) else None
        except Exception:
            logger.exception("sendMessage failed (chat=%s)", chat_id)
            return None

    async def _edit_text(self, chat_id: int, message_id: int, text: str) -> bool:
        try:
            await self.api("editMessageText", chat_id=chat_id, message_id=message_id, text=text)
            return True
        except Exception as exc:  # includes "message is not modified" etc.
            logger.warning("editMessageText failed (chat=%s): %s", chat_id, exc)
            return False

    # -------------------------------------------------------------- polling

    async def run(self) -> None:
        self._running = True
        try:
            try:
                me = await self.api("getMe")
                self.username = me.get("username")
                logger.info("Telegram bot started as @%s", self.username)
            except Exception:
                logger.exception("telegram getMe failed; bot not started")
                return
            await self._drop_backlog()
            backoff = 1.0
            while self._running:
                try:
                    updates = await self.api(
                        "getUpdates",
                        offset=self.offset,
                        timeout=self.poll_timeout,
                        allowed_updates=["message"],
                    )
                    backoff = 1.0
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("getUpdates failed; retrying in %.0fs", backoff)
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                    continue
                for upd in updates or []:
                    self.offset = upd["update_id"] + 1
                    task = asyncio.create_task(self._safe_handle(upd))
                    self._tasks.add(task)
                    task.add_done_callback(self._tasks.discard)
        finally:
            for task in list(self._tasks):
                task.cancel()
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            if self._owns_client:
                try:
                    await self.client.aclose()
                except Exception:
                    pass

    async def _drop_backlog(self) -> None:
        """Discard updates pending before this start (no answers to stale messages)."""
        try:
            pending = await self.api(
                "getUpdates", offset=-1, timeout=0, limit=1, allowed_updates=["message"]
            )
            if pending:
                self.offset = pending[-1]["update_id"] + 1
        except Exception:
            logger.exception("backlog drop failed")

    async def stop(self) -> None:
        self._running = False

    async def _safe_handle(self, update: Dict[str, Any]) -> None:
        try:
            await self.handle_update(update)
        except Exception:
            logger.exception("failed to handle update %s", update.get("update_id"))


    # -------------------------------------------------------------- routing

    async def handle_update(self, update: Dict[str, Any]) -> None:
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return
        chat = msg.get("chat") or {}
        if chat.get("type") != "private":
            return  # bot answers only in private chats
        chat_id = chat.get("id")
        if chat_id is None:
            return
        text = (msg.get("text") or "").strip()
        if not text:
            return  # stickers/media — ignore
        if text.startswith("/"):
            cmd, arg = parse_command(text)
            await self._dispatch_command(chat_id, cmd, arg, msg)
        else:
            await self._handle_question(chat_id, text)

    async def _dispatch_command(self, chat_id: int, cmd: str, arg: str, msg: Dict[str, Any]) -> None:
        if cmd == "start":
            await self._handle_start(chat_id, arg, msg)
        elif cmd == "collection":
            await self._handle_collection(chat_id, arg, msg)
        elif cmd == "help":
            await self._send_text(chat_id, self._help_text())
        else:
            await self._send_text(chat_id, UNKNOWN_COMMAND_TEXT)

    def _help_text(self) -> str:
        return HELP_TEXT.format(bot=self._bot_username())

    def _bot_username(self) -> str:
        return self.username or os.getenv("TG_BOT_USERNAME", "isdelal_bot")

    # ------------------------------------------------------------ commands

    async def _handle_start(self, chat_id: int, payload: str, msg: Dict[str, Any]) -> None:
        if not payload:
            binding = await self._get_binding(chat_id)
            if binding:
                await self._send_text(chat_id, START_NO_PAYLOAD_BOUND_TEXT.format(collection=binding))
            else:
                await self._send_text(chat_id, START_NO_PAYLOAD_TEXT.format(bot=self._bot_username()))
            return
        if not is_valid_collection_name(payload):
            await self._send_text(chat_id, BAD_PAYLOAD_TEXT)
            return
        await self._bind(chat_id, payload, msg)

    async def _handle_collection(self, chat_id: int, arg: str, msg: Dict[str, Any]) -> None:
        if not arg:
            await self._send_text(chat_id, BAD_COLLECTION_SYNTAX_TEXT)
            return
        if not is_valid_collection_name(arg):
            await self._send_text(chat_id, BAD_PAYLOAD_TEXT)
            return
        await self._bind(chat_id, arg, msg)

    async def _bind(self, chat_id: int, collection: str, msg: Dict[str, Any]) -> None:
        if not await asyncio.to_thread(collection_exists, collection):
            await self._send_text(chat_id, COLLECTION_NOT_FOUND_TEXT.format(collection=collection))
            return
        username = (msg.get("from") or {}).get("username")
        await self._set_binding(chat_id, collection, username)
        await self._send_text(chat_id, START_BOUND_TEXT.format(collection=collection))

    # ----------------------------------------------------------- persistence

    async def _get_binding(self, chat_id: int) -> Optional[str]:
        async with self.session_factory() as session:
            row = await session.execute(
                select(TelegramChat).where(TelegramChat.chat_id == chat_id)
            )
            tc = row.scalar_one_or_none()
            return tc.collection_name if tc else None

    async def _set_binding(self, chat_id: int, collection: str, username: Optional[str]) -> None:
        async with self.session_factory() as session:
            row = await session.execute(
                select(TelegramChat).where(TelegramChat.chat_id == chat_id)
            )
            tc = row.scalar_one_or_none()
            if tc:
                tc.collection_name = collection
                if username:
                    tc.username = username
                tc.updated_at = datetime.utcnow()
            else:
                session.add(
                    TelegramChat(chat_id=chat_id, collection_name=collection, username=username)
                )
            await session.commit()

    async def _find_site(self, collection: str) -> Optional[Site]:
        async with self.session_factory() as session:
            row = await session.execute(
                select(Site)
                .where(Site.collection_name == collection)
                .order_by(Site.id.asc())
                .limit(1)
            )
            return row.scalar_one_or_none()


    # ------------------------------------------------------------- questions

    async def _handle_question(self, chat_id: int, question: str) -> None:
        collection = await self._get_binding(chat_id)
        if not collection:
            await self._send_text(chat_id, NOT_BOUND_TEXT.format(bot=self._bot_username()))
            return
        if not self.limiter.allow(chat_id):
            await self._send_text(chat_id, LIMIT_TEXT)
            return
        async with self._answer_sem:
            await self._answer(chat_id, question, collection)

    async def _answer(self, chat_id: int, question: str, collection: str) -> None:
        active = _get_collection_active_ingests(collection)
        if active:
            await self._send_text(chat_id, PROCESSING_TEXT)
            return

        site = await self._find_site(collection)

        # 1) embed question (embed_texts returns (embeddings, jina_tokens) tuple)
        try:
            embs_result = await asyncio.to_thread(embed_texts, [question])
        except Exception:
            logger.exception("embed_texts failed (chat=%s)", chat_id)
            await self._send_text(chat_id, ERROR_TEXT)
            return
        embs, jina_tokens = embs_result if isinstance(embs_result, tuple) else (embs_result, 0)
        if not embs or not embs[0]:
            await self._send_text(chat_id, ERROR_TEXT)
            return
        q_emb = embs[0]

        # 2) query qdrant
        snippets = await asyncio.to_thread(
            query_and_build_context, q_emb, collection_name=collection
        )

        # 3) stream LLM answer with live edits (same pipeline as /chat/stream)
        await self._stream_answer(chat_id, question, snippets, site, jina_tokens)

    async def _stream_answer(
        self,
        chat_id: int,
        question: str,
        snippets: list,
        site: Optional[Site],
        jina_tokens: int,
    ) -> None:
        stop_typing = asyncio.Event()
        typing_task = asyncio.create_task(self._typing_loop(chat_id, stop_typing))
        usage: Dict[str, int] = {}
        full = ""
        shown = ""
        msg_id: Optional[int] = None
        last_edit = 0.0
        edits_enabled = True
        error: Optional[BaseException] = None

        def visible(text: str) -> str:
            return text if len(text) <= MESSAGE_LIMIT else text[:MESSAGE_LIMIT]

        async def push(force: bool = False) -> None:
            nonlocal shown, msg_id, last_edit, edits_enabled
            target = visible(full)
            if not target:
                return
            now = time.monotonic()
            if not force and now - last_edit < EDIT_INTERVAL:
                return
            if msg_id is None:
                msg_id = await self._send_text(chat_id, target)
                shown = target
                last_edit = now
                return
            if target == shown or not edits_enabled:
                return
            if await self._edit_text(chat_id, msg_id, target):
                shown = target
            else:
                edits_enabled = False
            last_edit = now


        try:
            deadline = time.monotonic() + float(os.getenv("TG_ANSWER_TIMEOUT", "120"))
            gen = call_llm_stream(question, snippets, usage=usage)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("answer timed out")
                try:
                    token = await asyncio.wait_for(
                        asyncio.to_thread(next, gen, _SENTINEL),
                        timeout=min(60.0, remaining),
                    )
                except asyncio.TimeoutError:
                    raise TimeoutError("answer timed out")
                if token is _SENTINEL:
                    break
                full += token
                await push()
        except asyncio.CancelledError:
            stop_typing.set()
            await asyncio.gather(typing_task, return_exceptions=True)
            raise
        except Exception as exc:
            error = exc
            logger.exception("LLM stream failed (chat=%s)", chat_id)
        finally:
            stop_typing.set()
            await asyncio.gather(typing_task, return_exceptions=True)

        if not full:
            if error is not None:
                await self._send_text(chat_id, ERROR_TEXT)
            return

        # final flush: split >4096 chars into follow-up messages
        parts = split_message(full)
        if msg_id is None:
            for part in parts:
                await self._send_text(chat_id, part)
        else:
            first_sent = False
            if parts[0] != shown:
                if edits_enabled:
                    first_sent = await self._edit_text(chat_id, msg_id, parts[0])
                if not first_sent:
                    for part in parts:
                        await self._send_text(chat_id, part)
                    return
            for part in parts[1:]:
                await self._send_text(chat_id, part)

        await self._record_usage(site, jina_tokens, usage)

    async def _typing_loop(self, chat_id: int, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await self.api("sendChatAction", chat_id=chat_id, action="typing")
            except Exception:
                pass  # typing is cosmetic — never fail on it
            try:
                await asyncio.wait_for(stop.wait(), timeout=TYPING_INTERVAL)
            except asyncio.TimeoutError:
                continue

    async def _record_usage(
        self, site: Optional[Site], jina_tokens: int, usage: Dict[str, int]
    ) -> None:
        if site is None:
            return
        try:
            async with self.session_factory() as session:
                await record_deepseek_usage(
                    session, site.user_id, site.id, int(usage.get("total_tokens", 0))
                )
                if jina_tokens > 0:
                    await record_jina_usage(session, site.user_id, site.id, jina_tokens)
                await session.commit()
        except Exception:
            logger.exception("usage recording failed (site=%s)", site.id)

