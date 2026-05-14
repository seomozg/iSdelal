from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime


# ---------- Auth ----------
class AuthUser(BaseModel):
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"

class UserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Sites ----------
class SiteCreate(BaseModel):
    url: str

class SiteResponse(BaseModel):
    id: int
    user_id: int
    collection_name: str
    url: str
    widget_config: Dict[str, Any]
    pages_indexed: int
    created_at: datetime
    # computed stats
    deepseek_tokens: int = 0
    jina_tokens: int = 0
    chat_requests: int = 0

    class Config:
        from_attributes = True

class WidgetConfigUpdate(BaseModel):
    title: Optional[str] = None
    welcomeMessage: Optional[str] = None
    color: Optional[str] = None
    sendText: Optional[str] = None
    placeholder: Optional[str] = None


# ---------- Usage ----------
class UserStatsResponse(BaseModel):
    total_deepseek_tokens: int = 0
    total_jina_tokens: int = 0
    total_chat_requests: int = 0
    total_pages_indexed: int = 0
    sites: list = []


# ---------- Subscription ----------
class TariffResponse(BaseModel):
    id: int
    name: str
    pages_limit: int
    requests_limit: int
    price_rub_month: int
    description: Optional[str] = None

    class Config:
        from_attributes = True

class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    tariff: TariffResponse
    active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------- Payment ----------
class PaymentResponse(BaseModel):
    id: int
    amount: float
    tariff_name: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# Update forward references
TokenResponse.model_rebuild()