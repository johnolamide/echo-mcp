import json
import pickle
from typing import Any, Optional, Union, Dict, List
from datetime import datetime, timedelta
import redis.asyncio as redis
import asyncio
from contextlib import asynccontextmanager

from app.core.config import settings


class RedisManager:
    """Redis connection and cache management"""
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
    
    async def connect(self):
        """Initialize Redis connection"""
        if not settings.REDIS_ENABLED:
            return
            
        try:
            # Create connection pool
            self._connection_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Create Redis client
            self._redis = redis.Redis(
                connection_pool=self._connection_pool,
                decode_responses=False  # We'll handle encoding/decoding manually
            )
            
            # Test connection
            await self._redis.ping()
            print("✅ Redis connected successfully")
            
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            self._redis = None
    
    async def disconnect(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            if self._connection_pool:
                await self._connection_pool.disconnect()
            print("🔌 Redis disconnected")
    
    def is_connected(self) -> bool:
        """Check if Redis is connected and available"""
        return self._redis is not None and settings.REDIS_ENABLED
    
    @asynccontextmanager
    async def get_redis(self):
        """Get Redis client with automatic fallback"""
        if not self.is_connected():
            yield None
        else:
            try:
                yield self._redis
            except Exception as e:
                print(f"⚠️ Redis operation failed: {e}")
                yield None


# Global Redis manager instance
redis_manager = RedisManager()


class CacheService:
    """High-level caching service with Redis backend"""
    
    def __init__(self):
        self.redis_manager = redis_manager
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for Redis storage"""
        if isinstance(data, (dict, list)):
            return json.dumps(data, default=str).encode('utf-8')
        elif isinstance(data, str):
            return data.encode('utf-8')
        else:
            return pickle.dumps(data)
    
    def _deserialize_data(self, data: bytes, data_type: str = 'auto') -> Any:
        """Deserialize data from Redis"""
        if not data:
            return None
            
        if data_type == 'json':
            return json.loads(data.decode('utf-8'))
        elif data_type == 'str':
            return data.decode('utf-8')
        elif data_type == 'pickle':
            return pickle.loads(data)
        else:  # auto-detect
            try:
                # Try JSON first
                return json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                try:
                    # Try pickle
                    return pickle.loads(data)
                except:
                    # Fall back to string
                    return data.decode('utf-8', errors='ignore')
    
    async def get(self, key: str, data_type: str = 'auto') -> Optional[Any]:
        """Get cached data by key"""
        async with self.redis_manager.get_redis() as redis_client:
            if not redis_client:
                return None
            
            try:
                data = await redis_client.get(key)
                if data:
                    return self._deserialize_data(data, data_type)
                return None
            except Exception as e:
                print(f"❌ Cache get error for key '{key}': {e}")
                return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached data with optional TTL"""
        async with self.redis_manager.get_redis() as redis_client:
            if not redis_client:
                return False
            
            try:
                serialized_data = self._serialize_data(value)
                
                if ttl:
                    await redis_client.setex(key, ttl, serialized_data)
                else:
                    await redis_client.set(key, serialized_data)
                
                return True
            except Exception as e:
                print(f"❌ Cache set error for key '{key}': {e}")
                return False
    
    async def delete(self, key: str) -> bool:
        """Delete cached data by key"""
        async with self.redis_manager.get_redis() as redis_client:
            if not redis_client:
                return False
            
            try:
                result = await redis_client.delete(key)
                return result > 0
            except Exception as e:
                print(f"❌ Cache delete error for key '{key}': {e}")
                return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching a pattern"""
        async with self.redis_manager.get_redis() as redis_client:
            if not redis_client:
                return 0
            
            try:
                keys = await redis_client.keys(pattern)
                if keys:
                    return await redis_client.delete(*keys)
                return 0
            except Exception as e:
                print(f"❌ Cache delete pattern error for pattern '{pattern}': {e}")
                return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        async with self.redis_manager.get_redis() as redis_client:
            if not redis_client:
                return False
            
            try:
                result = await redis_client.exists(key)
                return result > 0
            except Exception as e:
                print(f"❌ Cache exists error for key '{key}': {e}")
                return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on existing key"""
        async with self.redis_manager.get_redis() as redis_client:
            if not redis_client:
                return False
            
            try:
                result = await redis_client.expire(key, ttl)
                return result
            except Exception as e:
                print(f"❌ Cache expire error for key '{key}': {e}")
                return False
    
    # List operations
    async def list_push(self, key: str, *values: Any, ttl: Optional[int] = None) -> bool:
        """Push values to the end of a list"""
        async with self.redis_manager.get_redis() as redis_client:
            if not redis_client:
                return False
            
            try:
                serialized_values = [self._serialize_data(v) for v in values]
                await redis_client.rpush(key, *serialized_values)
                
                if ttl:
                    await redis_client.expire(key, ttl)
                
                return True
            except Exception as e:
                print(f"❌ Cache list_push error for key '{key}': {e}")
                return False
    
    async def list_get_range(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get range of values from a list"""
        async with self.redis_manager.get_redis() as redis_client:
            if not redis_client:
                return []
            
            try:
                data = await redis_client.lrange(key, start, end)
                return [self._deserialize_data(item) for item in data] if data else []
            except Exception as e:
                print(f"❌ Cache list_get_range error for key '{key}': {e}")
                return []
    
    async def list_length(self, key: str) -> int:
        """Get length of a list"""
        async with self.redis_manager.get_redis() as redis_client:
            if not redis_client:
                return 0
            
            try:
                return await redis_client.llen(key)
            except Exception as e:
                print(f"❌ Cache list_length error for key '{key}': {e}")
                return 0
    
    # Hash operations
    async def hash_set(self, key: str, field: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set field in hash"""
        async with self.redis_manager.get_redis() as redis_client:
            if not redis_client:
                return False
            
            try:
                serialized_value = self._serialize_data(value)
                await redis_client.hset(key, field, serialized_value)
                
                if ttl:
                    await redis_client.expire(key, ttl)
                
                return True
            except Exception as e:
                print(f"❌ Cache hash_set error for key '{key}', field '{field}': {e}")
                return False
    
    async def hash_get(self, key: str, field: str) -> Optional[Any]:
        """Get field from hash"""
        async with self.redis_manager.get_redis() as redis_client:
            if not redis_client:
                return None
            
            try:
                data = await redis_client.hget(key, field)
                return self._deserialize_data(data) if data else None
            except Exception as e:
                print(f"❌ Cache hash_get error for key '{key}', field '{field}': {e}")
                return None
    
    async def hash_get_all(self, key: str) -> Dict[str, Any]:
        """Get all fields from hash"""
        async with self.redis_manager.get_redis() as redis_client:
            if not redis_client:
                return {}
            
            try:
                data = await redis_client.hgetall(key)
                return {
                    k.decode('utf-8'): self._deserialize_data(v) 
                    for k, v in data.items()
                } if data else {}
            except Exception as e:
                print(f"❌ Cache hash_get_all error for key '{key}': {e}")
                return {}


# Global cache service instance
cache_service = CacheService()


# Cache key generators
class CacheKeys:
    """Cache key generators for different data types"""
    
    @staticmethod
    def user(user_id: int) -> str:
        return f"user:{user_id}"
    
    @staticmethod
    def user_session(token: str) -> str:
        return f"session:{token}"
    
    @staticmethod
    def chat_room(room_id: int) -> str:
        return f"chat:room:{room_id}"
    
    @staticmethod
    def chat_messages(room_id: int, page: int = 0) -> str:
        return f"chat:messages:{room_id}:page:{page}"
    
    @staticmethod
    def direct_messages(user1_id: int, user2_id: int, page: int = 0) -> str:
        # Ensure consistent ordering
        user_ids = sorted([user1_id, user2_id])
        return f"chat:direct:{user_ids[0]}:{user_ids[1]}:page:{page}"
    
    @staticmethod
    def user_conversations(user_id: int) -> str:
        return f"chat:conversations:{user_id}"
    
    @staticmethod
    def active_users_in_room(room_id: int) -> str:
        return f"chat:active_users:{room_id}"
    
    @staticmethod
    def online_users() -> str:
        return "users:online"
    
    @staticmethod
    def food_restaurants(query_hash: str) -> str:
        return f"food:restaurants:{query_hash}"
    
    @staticmethod
    def ride_fare_estimate(query_hash: str) -> str:
        return f"ride:fare:{query_hash}"


# Convenience functions
async def get_cached_user(user_id: int):
    """Get cached user data"""
    return await cache_service.get(CacheKeys.user(user_id))

async def cache_user(user_id: int, user_data: Dict):
    """Cache user data"""
    return await cache_service.set(
        CacheKeys.user(user_id), 
        user_data, 
        settings.USER_CACHE_TTL_SECONDS
    )

async def invalidate_user_cache(user_id: int):
    """Invalidate user cache"""
    await cache_service.delete(CacheKeys.user(user_id))
