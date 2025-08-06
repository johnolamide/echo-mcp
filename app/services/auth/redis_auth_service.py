import hashlib
import secrets
from typing import Optional, Dict, Any
from sqlmodel import Session, select
from datetime import datetime, timedelta

from app.models.auth import SessionToken, UserSession
from app.models.user import User
from app.services.auth import AuthService
from app.core.redis import cache_service, CacheKeys, settings


class RedisAuthService(AuthService):
    """Enhanced authentication service with Redis session caching"""
    
    def __init__(self, session: Session):
        super().__init__(session)
        self.cache = cache_service
    
    async def create_session_token(self, user_id: int) -> SessionToken:
        """Create session token with Redis caching"""
        # Generate token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Create database session
        user_session = UserSession(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )\n        
        self.session.add(user_session)
        self.session.commit()
        self.session.refresh(user_session)
        
        # Cache the session
        await self._cache_session(token, user_id, expires_at)
        
        return SessionToken(
            access_token=token,
            token_type=\"bearer\",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    async def get_user_from_token(self, token: str) -> Optional[User]:
        \"\"\"Get user from token with Redis caching\"\"\"
        # Try cache first
        cache_key = CacheKeys.user_session(token)
        cached_session = await self.cache.get(cache_key)
        
        if cached_session:
            user_id = cached_session.get('user_id')
            expires_at_str = cached_session.get('expires_at')
            
            if user_id and expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                
                # Check if token is still valid
                if datetime.utcnow() < expires_at:
                    # Get user from cache or database
                    user = await self._get_cached_user(user_id)
                    if user:
                        # Extend session cache TTL on access
                        remaining_seconds = int((expires_at - datetime.utcnow()).total_seconds())
                        await self.cache.expire(cache_key, remaining_seconds)
                    return user
                else:
                    # Token expired, remove from cache
                    await self.cache.delete(cache_key)
                    return None
        
        # Fallback to database
        return super().get_user_from_token(token)
    
    async def invalidate_token(self, token: str) -> bool:
        \"\"\"Invalidate token and remove from cache\"\"\"
        # Remove from cache
        cache_key = CacheKeys.user_session(token)
        await self.cache.delete(cache_key)
        
        # Remove from database
        return super().invalidate_token(token)
    
    async def invalidate_user_sessions(self, user_id: int) -> int:
        \"\"\"Invalidate all sessions for a user\"\"\"
        # Get all sessions for user from database
        statement = select(UserSession).where(UserSession.user_id == user_id)
        user_sessions = list(self.session.exec(statement).all())
        
        # Remove from cache
        for user_session in user_sessions:
            cache_key = CacheKeys.user_session(user_session.token)
            await self.cache.delete(cache_key)
        
        # Remove from database
        return super().invalidate_user_sessions(user_id)
    
    async def refresh_token(self, old_token: str) -> Optional[SessionToken]:
        \"\"\"Refresh token with cache update\"\"\"
        # Get user from old token
        user = await self.get_user_from_token(old_token)
        if not user:
            return None
        
        # Invalidate old token
        await self.invalidate_token(old_token)
        
        # Create new token
        return await self.create_session_token(user.id)
    
    async def get_active_sessions_count(self, user_id: int) -> int:
        \"\"\"Get count of active sessions for user\"\"\"
        cache_key = f\"user:sessions:count:{user_id}\"
        
        count = await self.cache.get(cache_key)
        if count is not None:
            return int(count)
        
        # Calculate from database
        statement = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.expires_at > datetime.utcnow()
        )
        sessions = list(self.session.exec(statement).all())
        count = len(sessions)
        
        # Cache for 5 minutes
        await self.cache.set(cache_key, count, 300)
        return count
    
    async def cleanup_expired_sessions(self) -> int:
        \"\"\"Clean up expired sessions from database and cache\"\"\"
        # Get expired sessions
        statement = select(UserSession).where(UserSession.expires_at <= datetime.utcnow())
        expired_sessions = list(self.session.exec(statement).all())
        
        # Remove from cache
        for session in expired_sessions:
            cache_key = CacheKeys.user_session(session.token)
            await self.cache.delete(cache_key)
        
        # Remove from database
        return super().cleanup_expired_sessions()
    
    # User caching methods
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        \"\"\"Get user by email with caching\"\"\"
        cache_key = f\"user:email:{email}\"
        
        cached_user_data = await self.cache.get(cache_key)
        if cached_user_data:
            return User(**cached_user_data)
        
        # Get from database
        user = super().get_user_by_email(email)
        
        if user:
            # Cache user data
            await self._cache_user_data(user)
            # Cache email->user mapping
            await self.cache.set(
                cache_key, 
                user.model_dump(), 
                settings.USER_CACHE_TTL_SECONDS
            )
        
        return user
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        \"\"\"Get user by ID with caching\"\"\"
        return await self._get_cached_user(user_id)
    
    # Private helper methods
    
    async def _cache_session(self, token: str, user_id: int, expires_at: datetime):
        \"\"\"Cache session data\"\"\"
        cache_key = CacheKeys.user_session(token)
        session_data = {
            'user_id': user_id,
            'expires_at': expires_at.isoformat(),
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Cache until expiration
        ttl = int((expires_at - datetime.utcnow()).total_seconds())
        await self.cache.set(cache_key, session_data, ttl)
    
    async def _get_cached_user(self, user_id: int) -> Optional[User]:
        \"\"\"Get user from cache or database\"\"\"
        cache_key = CacheKeys.user(user_id)
        
        cached_user_data = await self.cache.get(cache_key)
        if cached_user_data:
            return User(**cached_user_data)
        
        # Get from database
        user = self.session.get(User, user_id)
        
        if user:
            await self._cache_user_data(user)
        
        return user
    
    async def _cache_user_data(self, user: User):
        \"\"\"Cache user data\"\"\"
        cache_key = CacheKeys.user(user.id)
        await self.cache.set(
            cache_key,
            user.model_dump(),
            settings.USER_CACHE_TTL_SECONDS
        )
    
    async def invalidate_user_cache(self, user_id: int):
        \"\"\"Invalidate user cache\"\"\"
        cache_key = CacheKeys.user(user_id)
        await self.cache.delete(cache_key)
        
        # Also invalidate any email-based cache entries
        # This would require keeping track of user emails, or using a pattern
        await self.cache.delete_pattern(f\"user:email:*\")


# Factory function
async def get_redis_auth_service(session: Session) -> RedisAuthService:
    \"\"\"Get Redis-enhanced auth service instance\"\"\"
    return RedisAuthService(session)
