"""Client documents: parse (PDF/XLSX/Google), index into Qdrant, delete.

Documents live in the same Qdrant collection as the site content, so the RAG
answer pipeline (embed -> search -> LLM) picks them up without any changes.
Every document point carries `document_id` in its payload, which is how we
delete a document's chunks without touching the website chunks.
"""
import asyncio
import csv
import io
import re
import uuid

import requests
from qdrant_client import models

from .database import async_session_factory
from .embeddings import embed_texts
from .models import Document, Site
from .qdrant_client import get_qdrant_client
from .utils import chunk_text

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_DOC_CHUNKS = 200
ALLOWED_EXTENSIONS = (".pdf", ".xlsx")

# Google Docs/Sheets share URLs -> export endpoints (doc must be public: "Anyone with the link")
DOC_URL_RE = re.compile(r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)")
SHEET_URL_RE = re.compile(r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)")


class DocumentError(Exception):
    """Document processing error with a user-friendly message."""


def parse_pdf(data: bytes) -> str:
    """Extract plain text from a PDF file."""
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as e:
        raise DocumentError(f"Не удалось прочитать PDF: {e}") from e

    if len(text.split()) < 5:
        raise DocumentError(
            "Не удалось извлечь текст из PDF (возможно, это скан без текстового слоя)"
        )
    return text


def parse_xlsx(data: bytes) -> str:
    """Extract text from all worksheets of an Excel file (cells joined by spaces)."""
    from openpyxl import load_workbook

    try:
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as e:
        raise DocumentError(f"Не удалось прочитать Excel-файл: {e}") from e

    rows = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            cells = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
            if cells:
                rows.append(" | ".join(cells))
    wb.close()

    text = "\n".join(rows)
    if len(text.split()) < 5:
        raise DocumentError("Excel-файл не содержит данных")
    return text


def google_export_target(url: str) -> tuple[str, str]:
    """Classify a Google Docs/Sheets URL and build its export URL.

    Returns (source_type, export_url); raises DocumentError for other URLs.
    """
    doc = DOC_URL_RE.search(url)
    if doc:
        return "google_doc", f"https://docs.google.com/document/d/{doc.group(1)}/export?format=txt"
    sheet = SHEET_URL_RE.search(url)
    if sheet:
        return "google_sheet", f"https://docs.google.com/spreadsheets/d/{sheet.group(1)}/export?format=csv"
    raise DocumentError(
        "Не распознана ссылка. Поддерживаются Google Docs "
        "(docs.google.com/document/...) и Google Sheets (docs.google.com/spreadsheets/...)"
    )


def fetch_google_document(url: str) -> str:
    """Fetch a public Google Doc/Sheet via its export URL and return plain text."""
    source_type, export_url = google_export_target(url)
    try:
        resp = requests.get(export_url, timeout=30, allow_redirects=True)
    except Exception as e:
        raise DocumentError(f"Не удалось загрузить документ: {e}") from e

    if resp.status_code != 200:
        raise DocumentError(f"Google вернул ошибку {resp.status_code} при экспорте документа")
    if "html" in resp.headers.get("Content-Type", "").lower():
        raise DocumentError(
            "Документ недоступен по прямой ссылке. Опубликуйте его: "
            "Файл → Доступ → Все, у кого есть ссылка → Читатель."
        )

    if source_type == "google_sheet":
        return _csv_to_text(resp.text)
    return resp.text


def _csv_to_text(csv_text: str) -> str:
    """Render CSV rows as 'cell | cell' lines so chunking keeps rows intact."""
    lines = []
    for row in csv.reader(io.StringIO(csv_text)):
        cells = [cell.strip() for cell in row if cell.strip()]
        if cells:
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def validate_upload(file_name: str, size: int) -> str:
    """Check extension and size; returns normalized source_type ('pdf'|'xlsx')."""
    lower = (file_name or "").lower()
    if not lower.endswith(ALLOWED_EXTENSIONS):
        raise DocumentError(f"Поддерживаются только файлы {', '.join(ALLOWED_EXTENSIONS)}")
    if size > MAX_FILE_SIZE:
        raise DocumentError(f"Файл больше {MAX_FILE_SIZE // (1024 * 1024)} МБ")
    return "pdf" if lower.endswith(".pdf") else "xlsx"


def index_text(
    text: str,
    collection_name: str,
    document_id: int,
    source_type: str,
    document_name: str,
) -> int:
    """Chunk, embed and upsert document text into Qdrant. Returns chunk count."""
    chunks = chunk_text(text)[:MAX_DOC_CHUNKS]
    if not chunks:
        raise DocumentError("Не удалось разбить документ на фрагменты")

    result = embed_texts(chunks)
    embeddings = result[0] if isinstance(result, tuple) else result
    if not embeddings or not embeddings[0]:
        raise DocumentError("Не удалось создать эмбеддинги (проверьте JINA_API_KEY)")

    client = get_qdrant_client()
    vector_size = len(embeddings[0])
    try:
        exists = any(c.name == collection_name for c in client.get_collections().collections)
    except Exception:
        exists = False
    if not exists:
        client.create_collection(
            collection_name=collection_name,
            vectors_config={"size": vector_size, "distance": "Cosine"},
        )

    points = []
    for i, (chunk, vec) in enumerate(zip(chunks, embeddings)):
        points.append({
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"doc:{document_id}:{i}")),
            "vector": vec,
            "payload": {
                "text": chunk,
                "url": document_name,
                "chunk_id": i,
                "document_id": document_id,
                "source_type": source_type,
            },
        })
    client.upsert(collection_name=collection_name, points=points)
    return len(points)


def delete_document_chunks(document_id: int, collection_name: str) -> int:
    """Remove all Qdrant points belonging to a document. Returns deleted count."""
    client = get_qdrant_client()
    doc_filter = models.Filter(
        must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
    )
    try:
        result = client.count(collection_name=collection_name, count_filter=doc_filter, exact=True)
        client.delete(collection_name=collection_name, points_selector=doc_filter)
        return result.count
    except Exception:
        # Collection may not exist yet (nothing was indexed) — nothing to delete.
        return 0


async def ingest_document_background(
    document_id: int,
    file_bytes: bytes | None = None,
    google_url: str | None = None,
) -> None:
    """Parse a document (in a thread), index it into Qdrant, update DB status.

    `file_bytes` is set for PDF/XLSX uploads, `google_url` for Google Docs/Sheets.
    """
    doc = None
    async with async_session_factory() as session:
        doc = await session.get(Document, document_id)
        site = await session.get(Site, doc.site_id) if doc else None
        collection = site.collection_name if site else None

    try:
        if not doc or not collection:
            raise DocumentError("Документ или проект не найдены")

        if google_url:
            text = await asyncio.to_thread(fetch_google_document, google_url)
        else:
            parser = parse_pdf if doc.source_type == "pdf" else parse_xlsx
            text = await asyncio.to_thread(parser, file_bytes or b"")

        chunk_count = await asyncio.to_thread(
            index_text, text, collection, doc.id, doc.source_type, doc.name
        )

        async with async_session_factory() as session:
            row = await session.get(Document, document_id)
            if row:
                row.status = "completed"
                row.chunk_count = chunk_count
                await session.commit()
        print(f"📄 Document {document_id} indexed: {chunk_count} chunks")
    except DocumentError as e:
        await _mark_failed(document_id, str(e))
    except Exception as e:
        print(f"Document {document_id} ingest failed: {e}")
        await _mark_failed(document_id, f"Внутренняя ошибка при обработке: {e}")


async def _mark_failed(document_id: int, error: str) -> None:
    """Persist a failed status with the reason."""
    async with async_session_factory() as session:
        row = await session.get(Document, document_id)
        if row:
            row.status = "failed"
            row.error = error[:500]
            await session.commit()
    print(f"📄 Document {document_id} failed: {error}")

