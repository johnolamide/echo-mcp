from typing import List, Optional
from sqlmodel import Session, select
from datetime import datetime
import httpx
import math

from app.models.ride import (
    RideBooking, RideBookingCreate, RideBookingUpdate, RideStatus,
    RideFareEstimate, FareEstimateResponse, RideType
)
from app.core.config import settings


class RideService:
    def __init__(self, session: Session):
        self.session = session

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c

    def _estimate_fare_locally(self, estimate_request: RideFareEstimate) -> FareEstimateResponse:
        """Calculate fare estimate using local logic"""
        distance = self._calculate_distance(
            estimate_request.pickup_latitude,
            estimate_request.pickup_longitude,
            estimate_request.destination_latitude,
            estimate_request.destination_longitude
        )
        
        # Base fare rates per ride type
        base_fares = {
            RideType.ECONOMY: {"base": 3.0, "per_km": 1.5, "multiplier": 1.0},
            RideType.COMFORT: {"base": 5.0, "per_km": 2.0, "multiplier": 1.2},
            RideType.PREMIUM: {"base": 8.0, "per_km": 3.0, "multiplier": 1.5},
            RideType.SHARED: {"base": 2.0, "per_km": 1.0, "multiplier": 0.7}
        }
        
        fare_config = base_fares.get(estimate_request.ride_type, base_fares[RideType.ECONOMY])
        
        # Calculate base fare
        estimated_fare = (fare_config["base"] + 
                         (distance * fare_config["per_km"]) * fare_config["multiplier"])
        
        # Add surge pricing if needed (simplified)
        # In real implementation, this would consider demand, time of day, etc.
        estimated_fare = round(estimated_fare, 2)
        
        # Estimate duration (simplified - 30 km/h average speed)
        duration_minutes = max(5, int((distance / 30) * 60))
        
        return FareEstimateResponse(
            ride_type=estimate_request.ride_type,
            estimated_fare=estimated_fare,
            estimated_duration=f"{duration_minutes} minutes",
            estimated_distance=f"{distance:.1f} km"
        )

    async def get_fare_estimate(self, estimate_request: RideFareEstimate) -> FareEstimateResponse:
        """Get fare estimate using external API or local calculation"""
        
        if not settings.RIDE_API_BASE_URL:
            # Use local calculation
            return self._estimate_fare_locally(estimate_request)
        
        # Use external API
        async with httpx.AsyncClient() as client:
            try:
                fare_payload = {
                    "pickup_lat": estimate_request.pickup_latitude,
                    "pickup_lng": estimate_request.pickup_longitude,
                    "destination_lat": estimate_request.destination_latitude,
                    "destination_lng": estimate_request.destination_longitude,
                    "ride_type": estimate_request.ride_type.value
                }
                
                headers = {"Authorization": f"Bearer {settings.RIDE_API_KEY}"}
                
                response = await client.post(
                    f"{settings.RIDE_API_BASE_URL}/fare-estimate",
                    json=fare_payload,
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return FareEstimateResponse(
                        ride_type=estimate_request.ride_type,
                        estimated_fare=data.get("fare", 0.0),
                        estimated_duration=data.get("duration"),
                        estimated_distance=data.get("distance")
                    )
                
            except Exception as e:
                print(f"Error calling ride API for fare estimate: {e}")
        
        # Fallback to local calculation
        return self._estimate_fare_locally(estimate_request)

    async def create_booking(self, booking_data: RideBookingCreate, user_id: int) -> RideBooking:
        """Create a new ride booking"""
        # Get fare estimate
        fare_estimate = await self.get_fare_estimate(RideFareEstimate(
            pickup_latitude=booking_data.pickup_latitude,
            pickup_longitude=booking_data.pickup_longitude,
            destination_latitude=booking_data.destination_latitude,
            destination_longitude=booking_data.destination_longitude,
            ride_type=booking_data.ride_type
        ))
        
        booking = RideBooking(
            **booking_data.model_dump(),
            user_id=user_id,
            estimated_fare=fare_estimate.estimated_fare
        )
        
        # TODO: Book ride with external service
        if settings.RIDE_API_BASE_URL:
            await self._book_external_ride(booking)
        
        self.session.add(booking)
        self.session.commit()
        self.session.refresh(booking)
        return booking

    async def _book_external_ride(self, booking: RideBooking) -> None:
        """Book ride with external ride service"""
        async with httpx.AsyncClient() as client:
            try:
                booking_payload = {
                    "pickup_lat": booking.pickup_latitude,
                    "pickup_lng": booking.pickup_longitude,
                    "pickup_address": booking.pickup_address,
                    "destination_lat": booking.destination_latitude,
                    "destination_lng": booking.destination_longitude,
                    "destination_address": booking.destination_address,
                    "ride_type": booking.ride_type.value
                }
                
                headers = {"Authorization": f"Bearer {settings.RIDE_API_KEY}"}
                
                response = await client.post(
                    f"{settings.RIDE_API_BASE_URL}/bookings",
                    json=booking_payload,
                    headers=headers,
                    timeout=15.0
                )
                
                if response.status_code == 201:
                    result = response.json()
                    booking.external_booking_id = result.get("booking_id")
                    booking.status = RideStatus.DRIVER_ASSIGNED if result.get("driver_assigned") else RideStatus.PENDING
                    
                    if result.get("driver_info"):
                        booking.driver_info = result["driver_info"]
                    
                    if result.get("estimated_arrival"):
                        # Parse and set estimated arrival time
                        pass
                    
            except Exception as e:
                print(f"Error booking external ride: {e}")
                # Continue with local booking

    def get_booking_by_id(self, booking_id: int) -> Optional[RideBooking]:
        """Get ride booking by ID"""
        return self.session.get(RideBooking, booking_id)

    def get_user_bookings(self, user_id: int, skip: int = 0, limit: int = 20) -> List[RideBooking]:
        """Get user's ride bookings"""
        statement = (
            select(RideBooking)
            .where(RideBooking.user_id == user_id)
            .order_by(RideBooking.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.exec(statement).all())

    def update_booking(self, booking_id: int, booking_update: RideBookingUpdate) -> Optional[RideBooking]:
        """Update ride booking"""
        booking = self.get_booking_by_id(booking_id)
        if not booking:
            return None
        
        update_data = booking_update.model_dump(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            for field, value in update_data.items():
                setattr(booking, field, value)
            
            self.session.add(booking)
            self.session.commit()
            self.session.refresh(booking)
        
        return booking

    async def cancel_booking(self, booking_id: int, user_id: int) -> bool:
        """Cancel ride booking"""
        booking = self.get_booking_by_id(booking_id)
        if not booking or booking.user_id != user_id:
            return False
        
        # Check if booking can be cancelled
        if booking.status in [RideStatus.COMPLETED, RideStatus.CANCELLED]:
            return False
        
        # Cancel with external service if applicable
        if booking.external_booking_id and settings.RIDE_API_BASE_URL:
            await self._cancel_external_booking(booking.external_booking_id)
        
        booking.status = RideStatus.CANCELLED
        booking.updated_at = datetime.utcnow()
        
        self.session.add(booking)
        self.session.commit()
        return True

    async def _cancel_external_booking(self, external_booking_id: str) -> None:
        """Cancel booking with external ride service"""
        async with httpx.AsyncClient() as client:
            try:
                headers = {"Authorization": f"Bearer {settings.RIDE_API_KEY}"}
                
                response = await client.delete(
                    f"{settings.RIDE_API_BASE_URL}/bookings/{external_booking_id}",
                    headers=headers,
                    timeout=10.0
                )
                
                response.raise_for_status()
                
            except Exception as e:
                print(f"Error cancelling external booking: {e}")
                # Continue with local cancellation
