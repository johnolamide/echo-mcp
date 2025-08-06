from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlmodel import Session

from app.database.connection import get_session
from app.models.food import (
    FoodOrderCreate, FoodOrderRead, FoodOrderUpdate,
    RestaurantSearch, Restaurant
)
from app.models.user import User
from app.services.food import FoodService
from app.services.auth import AuthService
from app.core.auth_dependency import get_current_user

router = APIRouter()


@router.post("/search-restaurants", response_model=List[Restaurant])
async def search_restaurants(
    search_params: RestaurantSearch,
    session: Session = Depends(get_session)
):
    """Search for restaurants using external API"""
    food_service = FoodService(session)
    restaurants = await food_service.search_restaurants(search_params)
    return restaurants


@router.post("/orders", response_model=FoodOrderRead, status_code=status.HTTP_201_CREATED)
async def create_food_order(
    order_data: FoodOrderCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new food order"""
    food_service = FoodService(session)
    order = await food_service.create_order(order_data, current_user.id)
    return order


@router.get("/orders", response_model=List[FoodOrderRead])
async def get_user_food_orders(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get user's food orders"""
    food_service = FoodService(session)
    orders = food_service.get_user_orders(current_user.id, skip=skip, limit=limit)
    return orders


@router.get("/orders/{order_id}", response_model=FoodOrderRead)
async def get_food_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get food order by ID"""
    food_service = FoodService(session)
    order = food_service.get_order_by_id(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food order not found"
        )
    
    # Check if order belongs to user
    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return order


@router.put("/orders/{order_id}", response_model=FoodOrderRead)
async def update_food_order(
    order_id: int,
    order_update: FoodOrderUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update food order status"""
    food_service = FoodService(session)
    order = food_service.get_order_by_id(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food order not found"
        )
    
    # Check if order belongs to user
    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    updated_order = food_service.update_order(order_id, order_update)
    return updated_order


@router.delete("/orders/{order_id}")
async def cancel_food_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Cancel food order"""
    food_service = FoodService(session)
    success = await food_service.cancel_order(order_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to cancel order"
        )
    
    return {"message": "Order cancelled successfully"}
