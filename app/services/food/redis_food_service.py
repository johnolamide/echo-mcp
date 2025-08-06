import hashlib
import json
from typing import List, Optional, Dict, Any
from sqlmodel import Session

from app.models.food import RestaurantSearchRequest, RestaurantResponse, FoodOrderCreate, FoodOrder
from app.services.food import FoodService
from app.core.redis import cache_service, CacheKeys, settings


class RedisFoodService(FoodService):
    """Enhanced food service with Redis caching for external API responses"""
    
    def __init__(self, session: Session):
        super().__init__(session)
        self.cache = cache_service
    
    def _generate_search_hash(self, search_request: RestaurantSearchRequest) -> str:
        """Generate hash for search request to use as cache key"""
        # Create consistent hash from search parameters
        search_data = {
            'query': search_request.query or '',
            'latitude': search_request.latitude,
            'longitude': search_request.longitude,
            'cuisine_type': search_request.cuisine_type or '',
            'price_range': search_request.price_range or '',
            'radius': getattr(search_request, 'radius', 5000),  # Default radius
            'sort_by': getattr(search_request, 'sort_by', 'relevance')
        }
        
        # Sort keys for consistent hashing
        search_json = json.dumps(search_data, sort_keys=True)
        return hashlib.md5(search_json.encode()).hexdigest()
    
    async def search_restaurants(self, search_request: RestaurantSearchRequest) -> List[RestaurantResponse]:
        """Search restaurants with Redis caching"""
        # Generate cache key
        search_hash = self._generate_search_hash(search_request)
        cache_key = CacheKeys.food_restaurants(search_hash)
        
        # Try cache first
        cached_restaurants = await self.cache.get(cache_key)
        if cached_restaurants:
            return [RestaurantResponse(**restaurant) for restaurant in cached_restaurants]
        
        # Get from external API
        restaurants = super().search_restaurants(search_request)
        
        # Cache the results for 30 minutes (restaurants don't change frequently)
        if restaurants:
            restaurant_data = [restaurant.model_dump() for restaurant in restaurants]
            await self.cache.set(cache_key, restaurant_data, 1800)  # 30 minutes TTL
        
        return restaurants
    
    async def get_restaurant_details(self, restaurant_id: str) -> Optional[Dict[str, Any]]:
        """Get restaurant details with caching"""
        cache_key = f"food:restaurant_details:{restaurant_id}"
        
        cached_details = await self.cache.get(cache_key)
        if cached_details:
            return cached_details
        
        # Get from external API
        details = super().get_restaurant_details(restaurant_id)
        
        if details:
            # Cache for 1 hour (restaurant details change infrequently)
            await self.cache.set(cache_key, details, 3600)
        
        return details
    
    async def get_restaurant_menu(self, restaurant_id: str) -> List[Dict[str, Any]]:
        """Get restaurant menu with caching"""
        cache_key = f"food:restaurant_menu:{restaurant_id}"
        
        cached_menu = await self.cache.get(cache_key)
        if cached_menu:
            return cached_menu
        
        # Get from external API or database
        menu = super().get_restaurant_menu(restaurant_id)
        
        if menu:
            # Cache for 2 hours (menus don't change very often)
            await self.cache.set(cache_key, menu, 7200)
        
        return menu
    
    async def create_order(self, order_data: FoodOrderCreate, user_id: int) -> FoodOrder:
        """Create order and invalidate related caches"""
        order = super().create_order(order_data, user_id)
        
        # Invalidate user's order history cache
        await self._invalidate_user_orders_cache(user_id)
        
        # Update order statistics cache
        await self._update_order_stats_cache(order)
        
        return order
    
    async def get_user_orders(self, user_id: int, skip: int = 0, limit: int = 20) -> List[FoodOrder]:
        """Get user orders with caching"""
        cache_key = f"food:user_orders:{user_id}:skip:{skip}:limit:{limit}"
        
        cached_orders = await self.cache.get(cache_key)
        if cached_orders:
            return [FoodOrder(**order_data) for order_data in cached_orders]
        
        # Get from database
        orders = super().get_user_orders(user_id, skip, limit)
        
        # Cache for 10 minutes
        if orders:
            orders_data = [order.model_dump() for order in orders]
            await self.cache.set(cache_key, orders_data, 600)
        
        return orders
    
    async def get_order_by_id(self, order_id: int, user_id: int) -> Optional[FoodOrder]:
        """Get order by ID with caching"""
        cache_key = f"food:order:{order_id}:user:{user_id}"
        
        cached_order = await self.cache.get(cache_key)
        if cached_order:
            return FoodOrder(**cached_order)
        
        # Get from database
        order = super().get_order_by_id(order_id, user_id)
        
        if order:
            # Cache for 30 minutes
            await self.cache.set(cache_key, order.model_dump(), 1800)
        
        return order
    
    async def update_order_status(self, order_id: int, status: str, user_id: Optional[int] = None) -> bool:
        """Update order status and invalidate caches"""
        success = super().update_order_status(order_id, status, user_id)
        
        if success and user_id:
            # Invalidate related caches
            await self._invalidate_user_orders_cache(user_id)
            await self.cache.delete(f"food:order:{order_id}:user:{user_id}")
        
        return success
    
    # Analytics and Statistics
    
    async def get_popular_restaurants(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get popular restaurants with caching"""
        cache_key = f"food:popular_restaurants:limit:{limit}"
        
        cached_restaurants = await self.cache.get(cache_key)
        if cached_restaurants:
            return cached_restaurants
        
        # Calculate from database (simplified logic)
        # In a real implementation, this would analyze order frequency, ratings, etc.
        popular_restaurants = super().get_popular_restaurants(limit)
        
        # Cache for 4 hours (popularity changes slowly)
        if popular_restaurants:
            await self.cache.set(cache_key, popular_restaurants, 14400)
        
        return popular_restaurants
    
    async def get_user_order_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user order statistics with caching"""
        cache_key = f"food:user_stats:{user_id}"
        
        cached_stats = await self.cache.get(cache_key)
        if cached_stats:
            return cached_stats
        
        # Calculate from database
        stats = super().get_user_order_stats(user_id)
        
        # Cache for 1 hour
        if stats:
            await self.cache.set(cache_key, stats, 3600)
        
        return stats
    
    async def get_trending_cuisines(self) -> List[Dict[str, Any]]:
        """Get trending cuisines with caching"""
        cache_key = "food:trending_cuisines"
        
        cached_cuisines = await self.cache.get(cache_key)
        if cached_cuisines:
            return cached_cuisines
        
        # Calculate from recent orders
        trending_cuisines = super().get_trending_cuisines()
        
        # Cache for 6 hours
        if trending_cuisines:
            await self.cache.set(cache_key, trending_cuisines, 21600)
        
        return trending_cuisines
    
    # Location-based caching
    
    async def get_restaurants_by_location(self, latitude: float, longitude: float, radius: int = 5000) -> List[RestaurantResponse]:
        """Get restaurants by location with geospatial caching"""
        # Create location-based cache key
        location_key = f"loc_{latitude:.4f}_{longitude:.4f}_r{radius}"
        cache_key = f"food:restaurants_by_location:{location_key}"
        
        cached_restaurants = await self.cache.get(cache_key)
        if cached_restaurants:
            return [RestaurantResponse(**restaurant) for restaurant in cached_restaurants]
        
        # Create search request for location
        search_request = RestaurantSearchRequest(
            query="",
            latitude=latitude,
            longitude=longitude
        )
        
        restaurants = await self.search_restaurants(search_request)
        
        # Cache location-based results for 45 minutes
        if restaurants:
            restaurant_data = [restaurant.model_dump() for restaurant in restaurants]
            await self.cache.set(cache_key, restaurant_data, 2700)
        
        return restaurants
    
    # Cache management helpers
    
    async def _invalidate_user_orders_cache(self, user_id: int):
        """Invalidate all cached orders for a user"""
        pattern = f"food:user_orders:{user_id}:*"
        await self.cache.delete_pattern(pattern)
        
        # Also invalidate user stats
        await self.cache.delete(f"food:user_stats:{user_id}")
    
    async def _update_order_stats_cache(self, order: FoodOrder):
        """Update cached statistics when new order is placed"""
        # Invalidate global stats that might be affected
        await self.cache.delete_pattern("food:popular_restaurants:*")
        await self.cache.delete("food:trending_cuisines")
        
        # Could also update specific counters here
    
    async def clear_location_caches(self):
        """Clear all location-based caches (useful for data updates)"""
        await self.cache.delete_pattern("food:restaurants_by_location:*")
        await self.cache.delete_pattern("food:restaurants:*")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache usage statistics"""
        # This would require additional Redis commands to get key counts
        # For now, return basic info
        return {
            "redis_connected": self.cache.redis_manager.is_connected(),
            "cache_enabled": settings.REDIS_ENABLED,
            "message": "Cache statistics would show key counts and hit rates"
        }


# Factory function
def get_redis_food_service(session: Session) -> RedisFoodService:
    """Get Redis-enhanced food service instance"""
    return RedisFoodService(session)
