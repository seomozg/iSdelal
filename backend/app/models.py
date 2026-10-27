"""
SQLAlchemy ORM models (async). Tables are created automatically on startup by
`database.init_db()`; no external migration tool is used.
"""
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Boolean, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Tariff(Base):
    """Subscription plan: free, tariff_100, tariff_500, tariff_1000."""
    __tablename__ = "tariffs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)  # free, tariff_100, tariff_500, tariff_1000
    pages_limit = Column(Integer, nullable=False)
    requests_limit = Column(Integer, nullable=False, default=-1)  # -1 = unlimited
    price_rub_month = Column(Integer, nullable=False, default=0)
    description = Column(String, nullable=True)

    subscriptions = relationship("Subscription", back_populates="tariff")


class User(Base):
    """Registered user (Google Sign-In)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    google_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sites = relationship("Site", back_populates="user", lazy="dynamic")
    subscriptions = relationship("Subscription", back_populates="user")
    usage_stats = relationship("UsageStats", back_populates="user", lazy="dynamic")
    payments = relationship("Payment", back_populates="user")


class Site(Base):
    """A user's website project: URL + Qdrant collection + widget config."""
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    collection_name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    widget_config = Column(JSON, default=dict)
    pages_indexed = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="sites")
    usage_stats = relationship("UsageStats", back_populates="site", lazy="dynamic")
    documents = relationship(
        "Document",
        back_populates="site",
        lazy="dynamic",
        cascade="all, delete-orphan",  # deleting a site removes its documents too
    )


class UsageStats(Base):
    """Daily per-site usage counters (deepseek/jina tokens, chat requests)."""
    __tablename__ = "usage_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    deepseek_tokens = Column(Integer, default=0)
    jina_tokens = Column(Integer, default=0)
    chat_requests = Column(Integer, default=0)
    ingest_pages = Column(Integer, default=0)
    date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="usage_stats")
    site = relationship("Site", back_populates="usage_stats")


class Subscription(Base):
    """User's active tariff subscription."""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    tariff_id = Column(Integer, ForeignKey("tariffs.id"), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="subscriptions")
    tariff = relationship("Tariff", back_populates="subscriptions")


class Payment(Base):
    """YooKassa payment record."""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    tariff_name = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, succeeded, canceled
    yookassa_id = Column(String, nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="payments")


class TelegramChat(Base):
    """Binding of a Telegram chat to a Qdrant collection (RAG knowledge base)."""
    __tablename__ = "telegram_chats"

    chat_id = Column(BigInteger, primary_key=True)  # Telegram chat id (can exceed int32)
    collection_name = Column(String, nullable=False)
    username = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Document(Base):
    """A client document (PDF/XLSX/Google Doc/Sheet) indexed into a site's collection."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    name = Column(String, nullable=False)          # file name or Google Doc id
    source_type = Column(String, nullable=False)   # pdf | xlsx | google_doc | google_sheet
    source_url = Column(String, nullable=True)     # Google Doc/Sheet URL (for google_*)
    file_name = Column(String, nullable=True)      # original file name (for uploads)
    status = Column(String, default="processing")  # processing | completed | failed
    error = Column(String, nullable=True)          # failure reason (for status="failed")
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    site = relationship("Site", back_populates="documents")

