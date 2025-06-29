# app/models/user.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class UserModel(BaseModel):
    email: str
    hashed_password: str
    full_name: str
    role: str
    phone: str
    is_blocked: bool = False
    blocked_until: Optional[datetime] = None
    is_email_confirmed: bool = False
    confirmation_code: Optional[str] = None
    created_at: datetime
    address: Optional[str] = None
    telegram_id: Optional[str] = None
    vk_id: Optional[str] = None
