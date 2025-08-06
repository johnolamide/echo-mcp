from typing import List, Optional
from sqlmodel import Session, select
from datetime import datetime

from app.models.chat import (
    ChatRoom, ChatRoomCreate, ChatMessage, ChatMessageCreate, ChatMessageRead,
    DirectMessageCreate, DirectMessageRead, ConversationRead, RoomType
)
from app.models.user import User


def message_to_read(message: ChatMessage) -> ChatMessageRead:
    """Convert ChatMessage DB model to ChatMessageRead API model"""
    return ChatMessageRead(
        id=message.id,
        room_id=message.room_id,
        user_id=message.user_id,
        message_type=message.message_type,
        content=message.content,
        message_metadata=message.message_metadata,
        created_at=message.created_at
    )


class ChatService:
    def __init__(self, session: Session):
        self.session = session

    def create_chat_room(self, room_data: ChatRoomCreate, user_id: int) -> ChatRoom:
        """Create a new chat room"""
        room = ChatRoom(**room_data.model_dump(), created_by=user_id)
        self.session.add(room)
        self.session.commit()
        self.session.refresh(room)
        return room

    def get_chat_room(self, room_id: int) -> Optional[ChatRoom]:
        """Get chat room by ID"""
        return self.session.get(ChatRoom, room_id)

    def get_chat_rooms(self, skip: int = 0, limit: int = 100) -> List[ChatRoom]:
        """Get all active chat rooms"""
        statement = select(ChatRoom).where(ChatRoom.is_active == True).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

    def create_chat_message(self, message_data: ChatMessageCreate, user_id: int) -> ChatMessage:
        """Create a new chat message"""
        message = ChatMessage(**message_data.model_dump(), user_id=user_id)
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message

    def get_chat_messages(self, room_id: int, skip: int = 0, limit: int = 50) -> List[ChatMessage]:
        """Get messages from a chat room (ordered by creation time)"""
        statement = (
            select(ChatMessage)
            .where(ChatMessage.room_id == room_id)
            .order_by(ChatMessage.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        messages = list(self.session.exec(statement).all())
        return list(reversed(messages))  # Return in chronological order

    def get_message_by_id(self, message_id: int) -> Optional[ChatMessage]:
        """Get message by ID"""
        return self.session.get(ChatMessage, message_id)

    def delete_chat_room(self, room_id: int) -> bool:
        """Soft delete chat room"""
        room = self.get_chat_room(room_id)
        if not room:
            return False
        
        room.is_active = False
        self.session.add(room)
        self.session.commit()
        return True

    # Direct Messaging Methods
    
    def get_or_create_direct_room(self, user1_id: int, user2_id: int) -> ChatRoom:
        """Find existing direct message room or create new one between two users"""
        # Sort user IDs to ensure consistent room lookup
        participants = sorted([user1_id, user2_id])
        
        # Look for existing direct room with these participants
        statement = select(ChatRoom).where(
            ChatRoom.room_type == RoomType.DIRECT,
            ChatRoom.is_active == True,
            ChatRoom.participants == participants
        )
        existing_room = self.session.exec(statement).first()
        
        if existing_room:
            return existing_room
        
        # Create new direct message room
        direct_room = ChatRoom(
            name=None,  # Direct messages don't need names
            description=f"Direct conversation between users {user1_id} and {user2_id}",
            room_type=RoomType.DIRECT,
            created_by=user1_id,
            participants=participants
        )
        
        self.session.add(direct_room)
        self.session.commit()
        self.session.refresh(direct_room)
        return direct_room
    
    def send_direct_message(self, dm_data: DirectMessageCreate, sender_id: int) -> DirectMessageRead:
        """Send a direct message to a specific user"""
        # Verify recipient exists
        recipient = self.session.get(User, dm_data.recipient_user_id)
        if not recipient:
            raise ValueError(f"Recipient user {dm_data.recipient_user_id} not found")
        
        # Get or create direct message room
        room = self.get_or_create_direct_room(sender_id, dm_data.recipient_user_id)
        
        # Create the message
        message_data = ChatMessageCreate(
            room_id=room.id,
            content=dm_data.content,
            message_type=dm_data.message_type,
            message_metadata=dm_data.message_metadata
        )
        
        message = self.create_chat_message(message_data, sender_id)
        
        # Convert to DirectMessageRead
        return DirectMessageRead(
            id=message.id,
            room_id=message.room_id,
            sender_id=sender_id,
            recipient_id=dm_data.recipient_user_id,
            content=message.content,
            message_type=message.message_type,
            message_metadata=message.message_metadata,
            created_at=message.created_at
        )
    
    def get_user_conversations(self, user_id: int) -> List[ConversationRead]:
        """Get all direct message conversations for a user"""
        # Find all direct rooms where user is a participant
        statement = select(ChatRoom).where(
            ChatRoom.room_type == RoomType.DIRECT,
            ChatRoom.is_active == True
        )
        
        rooms = self.session.exec(statement).all()
        conversations = []
        
        for room in rooms:
            if room.participants and user_id in room.participants:
                # Find the other user in the conversation
                other_user_id = None
                for participant_id in room.participants:
                    if participant_id != user_id:
                        other_user_id = participant_id
                        break
                
                if other_user_id:
                    # Get other user's info
                    other_user = self.session.get(User, other_user_id)
                    if other_user:
                        # Get last message in this room
                        last_msg_statement = select(ChatMessage).where(
                            ChatMessage.room_id == room.id
                        ).order_by(ChatMessage.created_at.desc()).limit(1)
                        
                        last_message = self.session.exec(last_msg_statement).first()
                        
                        conversations.append(ConversationRead(
                            room_id=room.id,
                            other_user_id=other_user_id,
                            other_username=other_user.username,
                            other_firstname=other_user.firstname,
                            other_lastname=other_user.lastname,
                            last_message=last_message.content if last_message else None,
                            last_message_at=last_message.created_at if last_message else None,
                            unread_count=0  # TODO: Implement read status tracking
                        ))
        
        # Sort by last message time
        conversations.sort(key=lambda c: c.last_message_at or datetime.min, reverse=True)
        return conversations
    
    def get_direct_messages_with_user(self, current_user_id: int, other_user_id: int, skip: int = 0, limit: int = 50) -> List[DirectMessageRead]:
        """Get direct message history between two users"""
        # Find the direct room between these users
        participants = sorted([current_user_id, other_user_id])
        
        statement = select(ChatRoom).where(
            ChatRoom.room_type == RoomType.DIRECT,
            ChatRoom.is_active == True,
            ChatRoom.participants == participants
        )
        
        room = self.session.exec(statement).first()
        if not room:
            return []  # No conversation exists
        
        # Get messages from this room
        messages = self.get_chat_messages(room.id, skip, limit)
        
        # Convert to DirectMessageRead format
        direct_messages = []
        for message in messages:
            recipient_id = other_user_id if message.user_id == current_user_id else current_user_id
            direct_messages.append(DirectMessageRead(
                id=message.id,
                room_id=message.room_id,
                sender_id=message.user_id,
                recipient_id=recipient_id,
                content=message.content,
                message_type=message.message_type,
                message_metadata=message.message_metadata,
                created_at=message.created_at
            ))
        
        return direct_messages
