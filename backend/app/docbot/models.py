"""ORM models for the document bot (its own database file, see DOCBOT DATABASE_URL)."""
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String

from ..database import Base


class DocbotCollection(Base):
    """A collection created by this bot (registry — Qdrant is shared with the site)."""
    __tablename__ = "docbot_collections"

    name = Column(String, primary_key=True)  # also valid as a Telegram deep-link payload
    created_by_chat = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DocbotDocument(Base):
    """A document (PDF/XLSX/Google Doc/Sheet) indexed into a collection."""
    __tablename__ = "docbot_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    collection_name = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)          # file name or Google Doc id
    source_type = Column(String, nullable=False)   # pdf | xlsx | google_doc | google_sheet
    source_url = Column(String, nullable=True)     # Google Doc/Sheet URL (for google_*)
    file_name = Column(String, nullable=True)      # original file name (for uploads)
    status = Column(String, default="processing")  # processing | completed | failed
    error = Column(String, nullable=True)          # failure reason (for status="failed")
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
