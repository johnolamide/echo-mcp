from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, JSON, Column
from enum import Enum


class RideStatus(str, Enum):
    PENDING = "pending"
    DRIVER_ASSIGNED = "driver_assigned"
    DRIVER_ARRIVING = "driver_arriving"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RideType(str, Enum):
    ECONOMY = "economy"
    COMFORT = "comfort"
    PREMIUM = "premium"
    SHARED = "shared"


class RideBooking(SQLModel, table=True):
    """Ride booking model"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    pickup_latitude: float
    pickup_longitude: float
    pickup_address: str
    destination_latitude: float
    destination_longitude: float
    destination_address: str
    ride_type: RideType
    estimated_fare: Optional[float] = None
    actual_fare: Optional[float] = None
    status: RideStatus = Field(default=RideStatus.PENDING)
    external_booking_id: Optional[str] = None  # ID from external ride service
    driver_info: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    estimated_arrival_time: Optional[datetime] = None
    pickup_time: Optional[datetime] = None
    drop_off_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class RideBookingCreate(SQLModel):
    """Create ride booking"""
    pickup_latitude: float
    pickup_longitude: float
    pickup_address: str
    destination_latitude: float
    destination_longitude: float
    destination_address: str
    ride_type: RideType


class RideBookingRead(SQLModel):
    """Read ride booking"""
    id: int
    user_id: int
    pickup_latitude: float
    pickup_longitude: float
    pickup_address: str
    destination_latitude: float
    destination_longitude: float
    destination_address: str
    ride_type: RideType
    estimated_fare: Optional[float] = None
    actual_fare: Optional[float] = None
    status: RideStatus
    external_booking_id: Optional[str] = None
    driver_info: Optional[Dict[str, Any]] = None
    estimated_arrival_time: Optional[datetime] = None
    pickup_time: Optional[datetime] = None
    drop_off_time: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class RideBookingUpdate(SQLModel):
    """Update ride booking"""
    status: Optional[RideStatus] = None
    actual_fare: Optional[float] = None
    driver_info: Optional[Dict[str, Any]] = None
    estimated_arrival_time: Optional[datetime] = None
    pickup_time: Optional[datetime] = None
    drop_off_time: Optional[datetime] = None


class RideFareEstimate(SQLModel):
    """Ride fare estimate request"""
    pickup_latitude: float
    pickup_longitude: float
    destination_latitude: float
    destination_longitude: float
    ride_type: RideType


class FareEstimateResponse(SQLModel):
    """Fare estimate response"""
    ride_type: RideType
    estimated_fare: float
    estimated_duration: Optional[str] = None
    estimated_distance: Optional[str] = None
