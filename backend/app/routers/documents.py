"""Document management: upload PDF/XLSX or link a Google Doc/Sheet to a site."""
import asyncio

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_session
from ..documents import (
    DocumentError,
    delete_document_chunks,
    google_export_target,
    ingest_document_background,
    validate_upload,
)
from ..models import Document, Site, User
from ..schemas import DocumentResponse

router = APIRouter(prefix="/sites", tags=["dashboard"])

# Keep references to running background tasks so they are not garbage-collected.
_background_tasks: set = set()


async def _get_user_site(site_id: int, user: User, session: AsyncSession) -> Site:
    """Fetch a site owned by the current user or raise 404."""
    result = await session.execute(
        select(Site).where(Site.id == site_id, Site.user_id == user.id)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


def _spawn(doc_id: int, file_bytes: bytes | None = None, google_url: str | None = None) -> None:
    task = asyncio.create_task(ingest_document_background(doc_id, file_bytes, google_url))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


@router.post("/{site_id}/documents", response_model=DocumentResponse, status_code=202)
async def add_document(
    site_id: int,
    file: UploadFile | None = File(None),
    url: str | None = Form(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Add a document: multipart `file` (.pdf/.xlsx) OR form field `url` (Google Doc/Sheet)."""
    site = await _get_user_site(site_id, user, session)

    if (file is None) == (url is None):
        raise HTTPException(status_code=400, detail="Provide either 'file' or 'url', not both")

    file_bytes: bytes | None = None
    google_url: str | None = None
    if file is not None:
        file_bytes = await file.read()
        try:
            source_type = validate_upload(file.filename or "", len(file_bytes))
        except DocumentError as e:
            raise HTTPException(status_code=400, detail=str(e))
        name = file.filename or "document"
    else:
        url = url.strip()
        try:
            source_type, _ = google_export_target(url)  # fail fast on bad URL
        except DocumentError as e:
            raise HTTPException(status_code=400, detail=str(e))
        google_url = url
        name = url.rstrip("/").rsplit("/", 1)[-1].split("?")[0] or url

    doc = Document(
        site_id=site.id,
        name=name,
        source_type=source_type,
        source_url=google_url,
        file_name=file.filename if file is not None else None,
        status="processing",
    )
    session.add(doc)
    await session.commit()

    _spawn(doc.id, file_bytes=file_bytes, google_url=google_url)
    return doc


@router.get("/{site_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    site_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all documents of a site (newest first)."""
    await _get_user_site(site_id, user, session)
    result = await session.execute(
        select(Document).where(Document.site_id == site_id).order_by(Document.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{site_id}/documents/{document_id}")
async def delete_document(
    site_id: int,
    document_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete a document: remove its chunks from Qdrant, then the DB record."""
    site = await _get_user_site(site_id, user, session)

    result = await session.execute(
        select(Document).where(Document.id == document_id, Document.site_id == site_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    removed = await asyncio.to_thread(
        delete_document_chunks, document_id, site.collection_name
    )
    await session.delete(doc)
    await session.commit()
    return {"status": "deleted", "chunks_removed": removed}
