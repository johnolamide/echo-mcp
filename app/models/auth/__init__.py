from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class AuthSession(SQLModel, table=True):
    """Track auth sessions - for custom auth flow"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    email: str = Field(index=True)
    session_token: str = Field(unique=True, index=True)
    expires_at: datetime
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EmailLogin(SQLModel):
    """Email login request"""
    email: str


class TokenResponse(SQLModel):
    """Token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthSessionRead(SQLModel):
    """Auth session read model"""
    id: int
    user_id: int
    email: str
    expires_at: datetime
    is_active: bool
    created_at: datetime
