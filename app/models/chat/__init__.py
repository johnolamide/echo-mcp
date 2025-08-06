from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlmodel import SQLModel, Field, JSON, Column
from enum import Enum


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"


class RoomType(str, Enum):
    """Room types to distinguish between group chats and direct messages"""
    GROUP = "group"
    DIRECT = "direct"


class ChatRoom(SQLModel, table=True):
    """Chat room model supporting both group chats and direct messages"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: Optional[str] = None  # Optional for direct messages
    description: Optional[str] = None
    room_type: RoomType = Field(default=RoomType.GROUP)
    is_active: bool = Field(default=True)
    created_by: int = Field(foreign_key="user.id")
    participants: Optional[List[int]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatMessage(SQLModel, table=True):
    """Chat message model"""
    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: int = Field(foreign_key="chatroom.id")
    user_id: int = Field(foreign_key="user.id")
    message_type: MessageType = Field(default=MessageType.TEXT)
    content: str
    message_metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatMessageCreate(SQLModel):
    """Create chat message"""
    room_id: int
    message_type: MessageType = MessageType.TEXT
    content: str
    message_metadata: Optional[Dict[str, Any]] = None


class ChatMessageRead(SQLModel):
    """Read chat message"""
    id: int
    room_id: int
    user_id: int
    message_type: MessageType
    content: str
    message_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class ChatRoomCreate(SQLModel):
    """Create chat room"""
    name: str
    description: Optional[str] = None


class ChatRoomRead(SQLModel):
    """Read chat room"""
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    created_by: int
    created_at: datetime


class DirectMessageCreate(SQLModel):
    """Create a direct message to a specific user"""
    recipient_user_id: int
    content: str
    message_type: MessageType = MessageType.TEXT
    message_metadata: Optional[Dict[str, Any]] = None


class DirectMessageRead(SQLModel):
    """Read direct message with sender/recipient info"""
    id: int
    room_id: int
    sender_id: int
    recipient_id: int
    content: str
    message_type: MessageType
    message_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class ConversationRead(SQLModel):
    """Conversation summary between two users"""
    room_id: int
    other_user_id: int
    other_username: str
    other_firstname: Optional[str] = None
    other_lastname: Optional[str] = None
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0


class WebSocketMessage(SQLModel):
    """WebSocket message format"""
    type: str  # "message", "join", "leave", "error", "direct_message"
    room_id: Optional[int] = None
    content: Optional[str] = None
    message_metadata: Optional[Dict[str, Any]] = None
