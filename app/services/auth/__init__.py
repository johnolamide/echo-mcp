import secrets
from typing import Optional
from datetime import datetime, timedelta
from sqlmodel import Session, select

from app.models.auth import AuthSession
from app.models.user import User
from app.core.config import settings


class AuthService:
    def __init__(self, session: Session):
        self.session = session

    def generate_session_token(self) -> str:
        """Generate a secure session token"""
        return secrets.token_urlsafe(32)

    def create_auth_session(self, user_id: int, email: str) -> AuthSession:
        """Create a new auth session"""
        session_token = self.generate_session_token()
        expires_at = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Deactivate existing sessions for this user
        self.deactivate_user_sessions(user_id)
        
        auth_session = AuthSession(
            user_id=user_id,
            email=email,
            session_token=session_token,
            expires_at=expires_at
        )
        
        self.session.add(auth_session)
        self.session.commit()
        self.session.refresh(auth_session)
        return auth_session

    def get_session_by_token(self, token: str) -> Optional[AuthSession]:
        """Get auth session by token"""
        statement = select(AuthSession).where(
            AuthSession.session_token == token,
            AuthSession.is_active == True,
            AuthSession.expires_at > datetime.utcnow()
        )
        return self.session.exec(statement).first()

    def deactivate_session(self, token: str) -> bool:
        """Deactivate a specific session"""
        auth_session = self.get_session_by_token(token)
        if not auth_session:
            return False
        
        auth_session.is_active = False
        self.session.add(auth_session)
        self.session.commit()
        return True

    def deactivate_user_sessions(self, user_id: int) -> None:
        """Deactivate all sessions for a user"""
        statement = select(AuthSession).where(
            AuthSession.user_id == user_id,
            AuthSession.is_active == True
        )
        sessions = self.session.exec(statement).all()
        
        for session_obj in sessions:
            session_obj.is_active = False
            self.session.add(session_obj)
        
        self.session.commit()

    def validate_session(self, token: str) -> Optional[User]:
        """Validate session token and return user"""
        auth_session = self.get_session_by_token(token)
        if not auth_session:
            return None
        
        # Get user
        user = self.session.get(User, auth_session.user_id)
        if not user or not user.is_active:
            return None
        
        return user

    def extend_session(self, token: str) -> Optional[AuthSession]:
        """Extend session expiry"""
        auth_session = self.get_session_by_token(token)
        if not auth_session:
            return None
        
        auth_session.expires_at = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        self.session.add(auth_session)
        self.session.commit()
        self.session.refresh(auth_session)
        return auth_session

    async def send_login_email(self, email: str, login_token: str) -> bool:
        """Send login email (placeholder for custom auth flow)"""
        # TODO: Implement email sending logic
        # This would integrate with your email service provider
        print(f"Login email would be sent to {email} with token: {login_token}")
        return True
