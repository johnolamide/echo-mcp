from typing import List, Optional
from sqlmodel import Session, select
from datetime import datetime
import httpx

from app.models.food import (
    FoodOrder, FoodOrderCreate, FoodOrderUpdate, OrderStatus,
    RestaurantSearch, Restaurant
)
from app.core.config import settings


class FoodService:
    def __init__(self, session: Session):
        self.session = session

    async def search_restaurants(self, search_params: RestaurantSearch) -> List[Restaurant]:
        """Search restaurants using external API"""
        # TODO: Integrate with real food delivery API (e.g., Uber Eats, DoorDash, etc.)
        # For now, return mock data
        
        if not settings.FOOD_API_BASE_URL:
            # Return mock restaurants
            mock_restaurants = [
                Restaurant(
                    id="rest_1",
                    name="Pizza Palace",
                    cuisine_type="Italian",
                    rating=4.5,
                    price_range="$$",
                    delivery_time="30-45 min",
                    image_url="https://example.com/pizza.jpg"
                ),
                Restaurant(
                    id="rest_2",
                    name="Burger Barn",
                    cuisine_type="American",
                    rating=4.2,
                    price_range="$",
                    delivery_time="20-30 min",
                    image_url="https://example.com/burger.jpg"
                ),
                Restaurant(
                    id="rest_3",
                    name="Sushi Spot",
                    cuisine_type="Japanese",
                    rating=4.8,
                    price_range="$$$",
                    delivery_time="40-55 min",
                    image_url="https://example.com/sushi.jpg"
                )
            ]
            
            # Filter based on search query
            if search_params.query:
                query_lower = search_params.query.lower()
                mock_restaurants = [
                    r for r in mock_restaurants 
                    if query_lower in r.name.lower() or query_lower in r.cuisine_type.lower()
                ]
            
            if search_params.cuisine_type:
                cuisine_lower = search_params.cuisine_type.lower()
                mock_restaurants = [
                    r for r in mock_restaurants 
                    if cuisine_lower in r.cuisine_type.lower()
                ]
            
            return mock_restaurants
        
        # Real API integration would go here
        async with httpx.AsyncClient() as client:
            # Example API call structure
            params = {}
            if search_params.query:
                params["query"] = search_params.query
            if search_params.latitude and search_params.longitude:
                params["lat"] = search_params.latitude
                params["lng"] = search_params.longitude
            if search_params.cuisine_type:
                params["cuisine"] = search_params.cuisine_type
            
            headers = {"Authorization": f"Bearer {settings.FOOD_API_KEY}"}
            
            try:
                response = await client.get(
                    f"{settings.FOOD_API_BASE_URL}/restaurants/search",
                    params=params,
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                # Parse response and return Restaurant objects
                return [Restaurant(**restaurant_data) for restaurant_data in data.get("restaurants", [])]
                
            except Exception as e:
                print(f"Error calling food API: {e}")
                return []

    async def create_order(self, order_data: FoodOrderCreate, user_id: int) -> FoodOrder:
        """Create a new food order"""
        order = FoodOrder(**order_data.model_dump(), user_id=user_id)
        
        # TODO: Place order with external service
        if settings.FOOD_API_BASE_URL:
            await self._place_external_order(order)
        
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    async def _place_external_order(self, order: FoodOrder) -> None:
        """Place order with external food service"""
        async with httpx.AsyncClient() as client:
            try:
                order_payload = {
                    "restaurant_id": order.restaurant_id,
                    "items": order.items,
                    "delivery_address": order.delivery_address,
                    "phone_number": order.phone_number,
                    "total_amount": order.total_amount
                }
                
                headers = {"Authorization": f"Bearer {settings.FOOD_API_KEY}"}
                
                response = await client.post(
                    f"{settings.FOOD_API_BASE_URL}/orders",
                    json=order_payload,
                    headers=headers,
                    timeout=15.0
                )
                
                if response.status_code == 201:
                    result = response.json()
                    order.external_order_id = result.get("order_id")
                    if result.get("estimated_delivery_time"):
                        # Parse and set estimated delivery time
                        pass
                    
            except Exception as e:
                print(f"Error placing external order: {e}")
                # Continue with local order creation

    def get_order_by_id(self, order_id: int) -> Optional[FoodOrder]:
        """Get food order by ID"""
        return self.session.get(FoodOrder, order_id)

    def get_user_orders(self, user_id: int, skip: int = 0, limit: int = 20) -> List[FoodOrder]:
        """Get user's food orders"""
        statement = (
            select(FoodOrder)
            .where(FoodOrder.user_id == user_id)
            .order_by(FoodOrder.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.exec(statement).all())

    def update_order(self, order_id: int, order_update: FoodOrderUpdate) -> Optional[FoodOrder]:
        """Update food order"""
        order = self.get_order_by_id(order_id)
        if not order:
            return None
        
        update_data = order_update.model_dump(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            for field, value in update_data.items():
                setattr(order, field, value)
            
            self.session.add(order)
            self.session.commit()
            self.session.refresh(order)
        
        return order

    async def cancel_order(self, order_id: int, user_id: int) -> bool:
        """Cancel food order"""
        order = self.get_order_by_id(order_id)
        if not order or order.user_id != user_id:
            return False
        
        # Check if order can be cancelled
        if order.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
            return False
        
        # Cancel with external service if applicable
        if order.external_order_id and settings.FOOD_API_BASE_URL:
            await self._cancel_external_order(order.external_order_id)
        
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        
        self.session.add(order)
        self.session.commit()
        return True

    async def _cancel_external_order(self, external_order_id: str) -> None:
        """Cancel order with external food service"""
        async with httpx.AsyncClient() as client:
            try:
                headers = {"Authorization": f"Bearer {settings.FOOD_API_KEY}"}
                
                response = await client.delete(
                    f"{settings.FOOD_API_BASE_URL}/orders/{external_order_id}",
                    headers=headers,
                    timeout=10.0
                )
                
                response.raise_for_status()
                
            except Exception as e:
                print(f"Error cancelling external order: {e}")
                # Continue with local cancellation
