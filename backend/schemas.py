from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class ContactBase(BaseModel):
    name: str
    phone_number: str
    callmebot_key: Optional[str] = ""

class ContactCreate(ContactBase):
    pass

class Contact(ContactBase):
    id: int
    user_id: int
    callmebot_key: Optional[str] = ""

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone_number: str

class UserCreate(UserBase):
    password: str
    emergency_contacts: List[ContactCreate]

class User(UserBase):
    id: int
    created_at: datetime
    emergency_contacts: List[Contact] = []

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class ChatMessage(BaseModel):
    id: int
    role: str
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True

class ChatSessionBase(BaseModel):
    title: str

class ChatSessionCreate(ChatSessionBase):
    pass

class ChatSession(ChatSessionBase):
    id: int
    user_id: int
    crisis_state: Optional[str] = "no_active_crisis"
    escalation_level: Optional[str] = "none"
    last_alert_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ChatSessionDetail(ChatSession):
    messages: List[ChatMessage] = []
