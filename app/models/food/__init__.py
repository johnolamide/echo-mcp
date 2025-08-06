from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, JSON, Column
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class FoodOrder(SQLModel, table=True):
    """Food order model"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    restaurant_id: str  # External restaurant ID
    restaurant_name: str
    items: List[Dict[str, Any]] = Field(sa_column=Column(JSON))
    total_amount: float
    delivery_address: str
    phone_number: str
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    external_order_id: Optional[str] = None  # ID from external food service
    estimated_delivery_time: Optional[datetime] = None
    actual_delivery_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class FoodOrderCreate(SQLModel):
    """Create food order"""
    restaurant_id: str
    restaurant_name: str
    items: List[Dict[str, Any]]
    total_amount: float
    delivery_address: str
    phone_number: str


class FoodOrderRead(SQLModel):
    """Read food order"""
    id: int
    user_id: int
    restaurant_id: str
    restaurant_name: str
    items: List[Dict[str, Any]]
    total_amount: float
    delivery_address: str
    phone_number: str
    status: OrderStatus
    external_order_id: Optional[str] = None
    estimated_delivery_time: Optional[datetime] = None
    actual_delivery_time: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class FoodOrderUpdate(SQLModel):
    """Update food order"""
    status: Optional[OrderStatus] = None
    estimated_delivery_time: Optional[datetime] = None
    actual_delivery_time: Optional[datetime] = None


class RestaurantSearch(SQLModel):
    """Restaurant search request"""
    query: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    cuisine_type: Optional[str] = None
    price_range: Optional[str] = None


class Restaurant(SQLModel):
    """Restaurant model for external API response"""
    id: str
    name: str
    cuisine_type: str
    rating: Optional[float] = None
    price_range: Optional[str] = None
    delivery_time: Optional[str] = None
    image_url: Optional[str] = None
