from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database.connection import get_session
from app.models.user import UserCreate, UserRead, UserUpdate
from app.services.user import UserService

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    session: Session = Depends(get_session)
):
    """Register a new user"""
    user_service = UserService(session)
    
    # Check if username already exists
    if user_service.check_username_exists(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    if user_service.check_email_exists(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        user = user_service.create_user(user_data)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    session: Session = Depends(get_session)
):
    """Get user by ID"""
    user_service = UserService(session)
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.get("/", response_model=List[UserRead])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """Get all users with pagination"""
    user_service = UserService(session)
    users = user_service.get_users(skip=skip, limit=limit)
    return users


@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    session: Session = Depends(get_session)
):
    """Update user"""
    user_service = UserService(session)
    
    # Check if username is being updated and already exists
    if user_update.username:
        existing_user = user_service.get_user_by_username(user_update.username)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Check if email is being updated and already exists
    if user_update.email:
        existing_user = user_service.get_user_by_email(user_update.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already taken"
            )
    
    user = user_service.update_user(user_id, user_update)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    session: Session = Depends(get_session)
):
    """Delete user (soft delete)"""
    user_service = UserService(session)
    success = user_service.delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deleted successfully"}
