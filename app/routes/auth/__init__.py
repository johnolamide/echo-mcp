from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database.connection import get_session
from app.models.auth import EmailLogin, TokenResponse
from app.models.user import User
from app.services.auth import AuthService
from app.services.user import UserService
from app.core.auth_dependency import get_current_user, get_current_user_and_token

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login_with_email(
    login_data: EmailLogin,
    session: Session = Depends(get_session)
):
    """Login with email (placeholder for custom auth flow)"""
    user_service = UserService(session)
    auth_service = AuthService(session)
    
    # Check if user exists
    user = user_service.get_user_by_email(login_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive"
        )
    
    # Create auth session
    auth_session = auth_service.create_auth_session(user.id, user.email)
    
    # In a real implementation, you would:
    # 1. Generate a login token
    # 2. Send it via email
    # 3. Return a temporary response asking user to check email
    # For now, we'll return the session token directly
    
    return TokenResponse(
        access_token=auth_session.session_token,
        token_type="bearer",
        expires_in=1800  # 30 minutes
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Logout and invalidate session"""
    auth_service = AuthService(session)
    
    # Deactivate all sessions for the current user
    # Since get_current_user already validated the token, we can trust current_user
    auth_service.deactivate_user_sessions(current_user.id)
    
    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def refresh_session(
    user_and_token: tuple[User, str] = Depends(get_current_user_and_token),
    session: Session = Depends(get_session)
):
    """Refresh session token"""
    current_user, token = user_and_token
    auth_service = AuthService(session)
    
    # Extend the current session
    auth_session = auth_service.extend_session(token)
    if not auth_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    return TokenResponse(
        access_token=auth_session.session_token,
        token_type="bearer",
        expires_in=1800
    )


@router.get("/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user"""
    return current_user
