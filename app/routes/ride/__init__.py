from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlmodel import Session

from app.database.connection import get_session
from app.models.ride import (
    RideBookingCreate, RideBookingRead, RideBookingUpdate,
    RideFareEstimate, FareEstimateResponse
)
from app.models.user import User
from app.services.ride import RideService
from app.services.auth import AuthService
from app.core.auth_dependency import get_current_user

router = APIRouter()


@router.post("/fare-estimate", response_model=FareEstimateResponse)
async def get_fare_estimate(
    estimate_request: RideFareEstimate,
    session: Session = Depends(get_session)
):
    """Get fare estimate for a ride"""
    ride_service = RideService(session)
    fare_estimate = await ride_service.get_fare_estimate(estimate_request)
    return fare_estimate


@router.post("/bookings", response_model=RideBookingRead, status_code=status.HTTP_201_CREATED)
async def create_ride_booking(
    booking_data: RideBookingCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new ride booking"""
    ride_service = RideService(session)
    booking = await ride_service.create_booking(booking_data, current_user.id)
    return booking


@router.get("/bookings", response_model=List[RideBookingRead])
async def get_user_ride_bookings(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get user's ride bookings"""
    ride_service = RideService(session)
    bookings = ride_service.get_user_bookings(current_user.id, skip=skip, limit=limit)
    return bookings


@router.get("/bookings/{booking_id}", response_model=RideBookingRead)
async def get_ride_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get ride booking by ID"""
    ride_service = RideService(session)
    booking = ride_service.get_booking_by_id(booking_id)
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ride booking not found"
        )
    
    # Check if booking belongs to user
    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return booking


@router.put("/bookings/{booking_id}", response_model=RideBookingRead)
async def update_ride_booking(
    booking_id: int,
    booking_update: RideBookingUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update ride booking status"""
    ride_service = RideService(session)
    booking = ride_service.get_booking_by_id(booking_id)
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ride booking not found"
        )
    
    # Check if booking belongs to user
    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    updated_booking = ride_service.update_booking(booking_id, booking_update)
    return updated_booking


@router.delete("/bookings/{booking_id}")
async def cancel_ride_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Cancel ride booking"""
    ride_service = RideService(session)
    success = await ride_service.cancel_booking(booking_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to cancel booking"
        )
    
    return {"message": "Ride booking cancelled successfully"}
