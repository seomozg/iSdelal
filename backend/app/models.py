from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import enum


class Tariff(Base):
    __tablename__ = "tariffs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)  # free, tariff_100, tariff_500, tariff_1000
    pages_limit = Column(Integer, nullable=False)
    requests_limit = Column(Integer, nullable=False, default=-1)  # -1 = unlimited
    price_rub_month = Column(Integer, nullable=False, default=0)
    description = Column(String, nullable=True)

    subscriptions = relationship("Subscription", back_populates="tariff")


class User(Base):
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


class UsageStats(Base):
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
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    tariff_name = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, succeeded, canceled
    yookassa_id = Column(String, nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="payments")