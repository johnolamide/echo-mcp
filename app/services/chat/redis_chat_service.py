import hashlib
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from datetime import datetime

from app.models.chat import (
    ChatRoom, ChatRoomCreate, ChatMessage, ChatMessageCreate, ChatMessageRead,
    DirectMessageCreate, DirectMessageRead, ConversationRead, RoomType
)
from app.models.user import User
from app.services.chat import ChatService, message_to_read
from app.core.redis import cache_service, CacheKeys, settings


class RedisChatService(ChatService):
    """Enhanced chat service with Redis caching for better performance"""
    
    def __init__(self, session: Session):
        super().__init__(session)
        self.cache = cache_service

    # Room Management with Caching
    
    async def create_chat_room(self, room_data: ChatRoomCreate, user_id: int) -> ChatRoom:
        """Create a new chat room and cache it"""
        room = super().create_chat_room(room_data, user_id)
        
        # Cache the room
        await self._cache_room(room)
        
        # Invalidate room lists
        await self.cache.delete_pattern("chat:rooms:*")
        
        return room
    
    async def get_chat_room(self, room_id: int) -> Optional[ChatRoom]:
        """Get chat room with Redis caching"""
        # Try cache first
        cache_key = CacheKeys.chat_room(room_id)
        cached_room = await self.cache.get(cache_key)
        
        if cached_room:
            # Convert dict back to ChatRoom model
            return ChatRoom(**cached_room)
        
        # Get from database
        room = super().get_chat_room(room_id)
        
        if room:
            await self._cache_room(room)
        
        return room
    
    async def get_chat_rooms(self, skip: int = 0, limit: int = 100) -> List[ChatRoom]:
        """Get chat rooms with caching"""
        cache_key = f"chat:rooms:skip:{skip}:limit:{limit}"
        cached_rooms = await self.cache.get(cache_key)
        
        if cached_rooms:
            return [ChatRoom(**room_data) for room_data in cached_rooms]
        
        # Get from database
        rooms = super().get_chat_rooms(skip, limit)
        
        # Cache the results
        rooms_data = [room.model_dump() for room in rooms]
        await self.cache.set(
            cache_key, 
            rooms_data, 
            settings.CHAT_CACHE_TTL_SECONDS
        )
        
        return rooms
    
    # Message Management with Caching
    
    async def create_chat_message(self, message_data: ChatMessageCreate, user_id: int) -> ChatMessage:
        """Create message and update caches"""
        message = super().create_chat_message(message_data, user_id)
        
        # Invalidate cached messages for this room
        await self._invalidate_room_message_cache(message_data.room_id)
        
        # Add to real-time message cache
        await self._add_message_to_cache(message)
        
        # Update conversation cache if it's a direct message
        room = await self.get_chat_room(message_data.room_id)
        if room and room.room_type == RoomType.DIRECT:
            await self._update_conversation_cache(room, message)
        
        return message
    
    async def get_chat_messages(self, room_id: int, skip: int = 0, limit: int = 50) -> List[ChatMessage]:
        """Get messages with Redis caching"""
        page = skip // limit
        cache_key = CacheKeys.chat_messages(room_id, page)
        
        # Try cache first
        cached_messages = await self.cache.get(cache_key)
        if cached_messages:
            return [ChatMessage(**msg_data) for msg_data in cached_messages]
        
        # Get from database
        messages = super().get_chat_messages(room_id, skip, limit)
        
        # Cache the results
        messages_data = [msg.model_dump() for msg in messages]
        await self.cache.set(
            cache_key,
            messages_data,
            settings.CHAT_CACHE_TTL_SECONDS
        )
        
        return messages
    
    async def get_recent_messages(self, room_id: int, limit: int = 20) -> List[ChatMessageRead]:
        """Get recent messages with aggressive caching for real-time chat"""
        cache_key = f"chat:recent_messages:{room_id}:limit:{limit}"
        
        cached_messages = await self.cache.get(cache_key)
        if cached_messages:
            return [ChatMessageRead(**msg_data) for msg_data in cached_messages]
        
        # Get from database
        messages = await self.get_chat_messages(room_id, 0, limit)
        message_reads = [message_to_read(msg) for msg in messages]
        
        # Cache with shorter TTL for real-time data
        messages_data = [msg.model_dump() for msg in message_reads]
        await self.cache.set(
            cache_key,
            messages_data,
            60  # 1 minute TTL for recent messages
        )
        
        return message_reads
    
    # Direct Messaging with Caching
    
    async def send_direct_message(self, dm_data: DirectMessageCreate, sender_id: int) -> DirectMessageRead:
        """Send direct message with caching"""
        direct_message = super().send_direct_message(dm_data, sender_id)
        
        # Update conversations cache for both users
        await self._invalidate_conversations_cache(sender_id)
        await self._invalidate_conversations_cache(dm_data.recipient_user_id)
        
        return direct_message
    
    async def get_user_conversations(self, user_id: int) -> List[ConversationRead]:
        """Get conversations with caching"""
        cache_key = CacheKeys.user_conversations(user_id)
        
        cached_conversations = await self.cache.get(cache_key)
        if cached_conversations:
            return [ConversationRead(**conv_data) for conv_data in cached_conversations]
        
        # Get from database
        conversations = super().get_user_conversations(user_id)
        
        # Cache the results
        conversations_data = [conv.model_dump() for conv in conversations]
        await self.cache.set(
            cache_key,
            conversations_data,
            settings.CHAT_CACHE_TTL_SECONDS
        )
        
        return conversations
    
    async def get_direct_messages_with_user(self, current_user_id: int, other_user_id: int, skip: int = 0, limit: int = 50) -> List[DirectMessageRead]:
        """Get direct messages with caching"""
        page = skip // limit
        cache_key = CacheKeys.direct_messages(current_user_id, other_user_id, page)
        
        cached_messages = await self.cache.get(cache_key)
        if cached_messages:
            return [DirectMessageRead(**msg_data) for msg_data in cached_messages]
        
        # Get from database
        direct_messages = super().get_direct_messages_with_user(current_user_id, other_user_id, skip, limit)
        
        # Cache the results
        messages_data = [msg.model_dump() for msg in direct_messages]
        await self.cache.set(
            cache_key,
            messages_data,
            settings.CHAT_CACHE_TTL_SECONDS
        )
        
        return direct_messages
    
    # WebSocket & Real-time Features
    
    async def add_user_to_room(self, room_id: int, user_id: int):
        """Track active users in room"""
        cache_key = CacheKeys.active_users_in_room(room_id)
        await self.cache.hash_set(cache_key, str(user_id), datetime.utcnow().isoformat(), ttl=3600)
    
    async def remove_user_from_room(self, room_id: int, user_id: int):
        """Remove user from active users in room"""
        cache_key = CacheKeys.active_users_in_room(room_id)
        # Note: Redis hash field deletion would need a separate method
        await self.cache.delete(f"{cache_key}:user:{user_id}")
    
    async def get_active_users_in_room(self, room_id: int) -> List[int]:
        """Get currently active users in a room"""
        cache_key = CacheKeys.active_users_in_room(room_id)
        active_users = await self.cache.hash_get_all(cache_key)
        return [int(user_id) for user_id in active_users.keys()] if active_users else []
    
    async def set_user_online(self, user_id: int):
        """Mark user as online"""
        cache_key = CacheKeys.online_users()
        await self.cache.hash_set(cache_key, str(user_id), datetime.utcnow().isoformat(), ttl=1800)  # 30 minutes
    
    async def set_user_offline(self, user_id: int):
        """Mark user as offline"""
        cache_key = CacheKeys.online_users()
        # Would need a hash delete field method
        await self.cache.delete(f"{cache_key}:user:{user_id}")
    
    async def get_online_users(self) -> List[int]:
        """Get list of currently online users"""
        cache_key = CacheKeys.online_users()
        online_users = await self.cache.hash_get_all(cache_key)
        return [int(user_id) for user_id in online_users.keys()] if online_users else []
    
    # Analytics & Statistics
    
    async def get_room_message_count(self, room_id: int) -> int:
        """Get cached message count for room"""
        cache_key = f"chat:room_stats:{room_id}:message_count"
        
        count = await self.cache.get(cache_key)
        if count is not None:
            return int(count)
        
        # Calculate from database
        statement = select(ChatMessage).where(ChatMessage.room_id == room_id)
        messages = list(self.session.exec(statement).all())
        count = len(messages)
        
        # Cache for 10 minutes
        await self.cache.set(cache_key, count, 600)
        return count
    
    async def get_user_message_count(self, user_id: int, room_id: Optional[int] = None) -> int:
        """Get cached message count for user"""
        cache_suffix = f"room:{room_id}" if room_id else "total"
        cache_key = f"chat:user_stats:{user_id}:message_count:{cache_suffix}"
        
        count = await self.cache.get(cache_key)
        if count is not None:
            return int(count)
        
        # Calculate from database
        statement = select(ChatMessage).where(ChatMessage.user_id == user_id)
        if room_id:
            statement = statement.where(ChatMessage.room_id == room_id)
        
        messages = list(self.session.exec(statement).all())
        count = len(messages)
        
        # Cache for 5 minutes
        await self.cache.set(cache_key, count, 300)
        return count
    
    # Private helper methods
    
    async def _cache_room(self, room: ChatRoom):
        """Cache room data"""
        cache_key = CacheKeys.chat_room(room.id)
        await self.cache.set(
            cache_key,
            room.model_dump(),
            settings.CHAT_CACHE_TTL_SECONDS
        )
    
    async def _invalidate_room_message_cache(self, room_id: int):
        """Invalidate all cached messages for a room"""
        pattern = f"chat:messages:{room_id}:*"
        await self.cache.delete_pattern(pattern)
        
        # Also invalidate recent messages
        recent_pattern = f"chat:recent_messages:{room_id}:*"
        await self.cache.delete_pattern(recent_pattern)
    
    async def _add_message_to_cache(self, message: ChatMessage):
        """Add new message to real-time cache"""
        # This could be used for real-time message streaming
        cache_key = f"chat:new_messages:{message.room_id}"
        message_data = message.model_dump()
        
        # Add to a list of recent messages (keep last 100)
        await self.cache.list_push(cache_key, message_data, ttl=300)
        
        # Trim list to keep only recent messages
        current_length = await self.cache.list_length(cache_key)
        if current_length > 100:
            # Would need a list trim method for this
            pass
    
    async def _update_conversation_cache(self, room: ChatRoom, message: ChatMessage):
        """Update conversation cache when new direct message arrives"""
        if room.participants:
            for user_id in room.participants:
                await self._invalidate_conversations_cache(user_id)
    
    async def _invalidate_conversations_cache(self, user_id: int):
        """Invalidate conversations cache for user"""
        cache_key = CacheKeys.user_conversations(user_id)
        await self.cache.delete(cache_key)


# Factory function to create Redis-enhanced chat service
async def get_redis_chat_service(session: Session) -> RedisChatService:
    """Get Redis-enhanced chat service instance"""
    return RedisChatService(session)
