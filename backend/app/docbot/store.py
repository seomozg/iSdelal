"""Database helpers for the document bot: bindings, documents, registry."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select

from ..database import async_session_factory
from ..models import TelegramChat
from .models import DocbotCollection, DocbotDocument


async def get_binding(chat_id: int) -> Optional[str]:
    """Collection this chat is bound to (TelegramChat is shared with the site bot)."""
    async with async_session_factory() as session:
        row = await session.execute(
            select(TelegramChat).where(TelegramChat.chat_id == chat_id)
        )
        tc = row.scalar_one_or_none()
        return tc.collection_name if tc else None


async def set_binding(chat_id: int, collection: str, username: Optional[str] = None) -> None:
    """Bind a chat to a collection (upsert)."""
    async with async_session_factory() as session:
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


async def add_collection(name: str, chat_id: int) -> None:
    """Register a bot-created collection (idempotent)."""
    async with async_session_factory() as session:
        existing = await session.get(DocbotCollection, name)
        if not existing:
            session.add(DocbotCollection(name=name, created_by_chat=chat_id))
            await session.commit()


async def list_collections() -> List[str]:
    """Names of collections created by this bot (newest first)."""
    async with async_session_factory() as session:
        rows = await session.execute(
            select(DocbotCollection).order_by(DocbotCollection.created_at.desc())
        )
        return [r.name for r in rows.scalars().all()]


async def add_document(
    collection_name: str,
    name: str,
    source_type: str,
    *,
    source_url: Optional[str] = None,
    file_name: Optional[str] = None,
    status: str = "processing",
) -> int:
    """Create a document row; returns its id."""
    async with async_session_factory() as session:
        doc = DocbotDocument(
            collection_name=collection_name,
            name=name,
            source_type=source_type,
            source_url=source_url,
            file_name=file_name,
            status=status,
        )
        session.add(doc)
        await session.commit()
        return doc.id


async def get_document(doc_id: int) -> Optional[DocbotDocument]:
    async with async_session_factory() as session:
        return await session.get(DocbotDocument, doc_id)


async def list_documents(collection_name: str) -> List[DocbotDocument]:
    """Documents of a collection ordered by id (stable numbering for /del)."""
    async with async_session_factory() as session:
        rows = await session.execute(
            select(DocbotDocument)
            .where(DocbotDocument.collection_name == collection_name)
            .order_by(DocbotDocument.id.asc())
        )
        return list(rows.scalars().all())


async def update_document(doc_id: int, **fields) -> None:
    """Update status/chunk_count/error of a document."""
    async with async_session_factory() as session:
        doc = await session.get(DocbotDocument, doc_id)
        if doc:
            for key, value in fields.items():
                setattr(doc, key, value)
            await session.commit()


async def delete_document(doc_id: int) -> None:
    async with async_session_factory() as session:
        doc = await session.get(DocbotDocument, doc_id)
        if doc:
            await session.delete(doc)
            await session.commit()
