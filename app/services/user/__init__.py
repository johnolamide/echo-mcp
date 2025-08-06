from typing import List, Optional
from sqlmodel import Session, select
from datetime import datetime

from app.models.user import User, UserCreate, UserUpdate
from app.database.connection import get_session


class UserService:
    def __init__(self, session: Session):
        self.session = session

    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user"""
        user = User(**user_data.model_dump())
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.session.get(User, user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        statement = select(User).where(User.email == email)
        return self.session.exec(statement).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        statement = select(User).where(User.username == username)
        return self.session.exec(statement).first()

    def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        statement = select(User).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

    def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """Update user"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        update_data = user_update.model_dump(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            for field, value in update_data.items():
                setattr(user, field, value)
            
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
        
        return user

    def delete_user(self, user_id: int) -> bool:
        """Soft delete user"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        self.session.add(user)
        self.session.commit()
        return True

    def check_username_exists(self, username: str) -> bool:
        """Check if username already exists"""
        return self.get_user_by_username(username) is not None

    def check_email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        return self.get_user_by_email(email) is not None
