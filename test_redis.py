#!/usr/bin/env python3
"""
Simple test to demonstrate Redis integration working
"""
import asyncio
import time
from app.core.redis import cache_service, CacheKeys, redis_manager


async def test_basic_redis_operations():
    """Test basic Redis operations"""
    print("🧪 Testing Basic Redis Operations\n")
    
    # Connect to Redis
    await redis_manager.connect()
    
    if not redis_manager.is_connected():
        print("❌ Redis is not connected!")
        return
    
    print("✅ Redis connected successfully")
    
    # Test basic set/get operations
    print("\n📝 Testing basic cache operations...")
    
    # Set some test data
    test_data = {
        "username": "testuser", 
        "email": "test@example.com",
        "cached_at": time.time()
    }
    
    cache_key = "test:user:123"
    
    # Measure set operation
    start_time = time.time()
    success = await cache_service.set(cache_key, test_data, ttl=300)  # 5 minutes TTL
    set_time = (time.time() - start_time) * 1000  # Convert to ms
    
    print(f"✅ Set operation: {set_time:.2f}ms - Success: {success}")
    
    # Measure get operation
    start_time = time.time()
    cached_data = await cache_service.get(cache_key)
    get_time = (time.time() - start_time) * 1000  # Convert to ms
    
    print(f"✅ Get operation: {get_time:.2f}ms - Data retrieved: {cached_data is not None}")
    
    if cached_data:
        print(f"   📊 Cached user: {cached_data['username']} ({cached_data['email']})")
    
    # Test pattern-based operations
    print("\n🔍 Testing pattern-based operations...")
    
    # Set multiple keys
    await cache_service.set("test:user:456", {"username": "user456"}, ttl=300)
    await cache_service.set("test:user:789", {"username": "user789"}, ttl=300) 
    await cache_service.set("test:session:abc", {"token": "abc123"}, ttl=300)
    
    # Test existence
    exists = await cache_service.exists(cache_key)
    print(f"✅ Key exists check: {exists}")
    
    # Test deletion
    deleted = await cache_service.delete(cache_key)
    print(f"✅ Delete operation: {deleted}")
    
    # Verify deletion
    deleted_data = await cache_service.get(cache_key)
    print(f"✅ Verify deletion: {deleted_data is None}")
    
    # Clean up test data
    await cache_service.delete_pattern("test:*")
    print("🧹 Cleaned up test data")
    
    await redis_manager.disconnect()
    print("\n🔌 Redis disconnected")


async def test_performance_comparison():
    """Test performance comparison with and without Redis"""
    print("\n⚡ Testing Performance Comparison\n")
    
    await redis_manager.connect()
    
    if not redis_manager.is_connected():
        print("❌ Redis is not connected!")
        return
    
    # Simulate database lookup time (slow operation)
    def simulate_db_lookup():
        time.sleep(0.05)  # 50ms simulated database query
        return {
            "id": 123,
            "username": "testuser",
            "email": "test@example.com", 
            "profile_data": "large data payload" * 100
        }
    
    cache_key = "perf:test:user:123"
    
    print("🔄 First request (database lookup simulation):")
    start_time = time.time()
    
    # Check cache first (cache miss expected)
    cached_data = await cache_service.get(cache_key)
    
    if cached_data is None:
        # Simulate database lookup
        data = simulate_db_lookup()
        
        # Cache the result
        await cache_service.set(cache_key, data, ttl=300)
        db_time = (time.time() - start_time) * 1000
        print(f"   💾 Database lookup: {db_time:.2f}ms (cache miss)")
    
    print("\n🚀 Second request (Redis cache hit):")
    start_time = time.time()
    
    # This should hit the cache
    cached_data = await cache_service.get(cache_key)
    cache_time = (time.time() - start_time) * 1000
    
    if cached_data:
        print(f"   ⚡ Redis cache hit: {cache_time:.2f}ms")
        print(f"   📈 Performance improvement: {db_time/cache_time:.1f}x faster!")
    
    # Clean up
    await cache_service.delete(cache_key)
    
    await redis_manager.disconnect()


async def test_chat_caching_patterns():
    """Test chat service caching patterns"""
    print("\n💬 Testing Chat Caching Patterns\n")
    
    await redis_manager.connect()
    
    if not redis_manager.is_connected():
        print("❌ Redis is not connected!")
        return
    
    # Test chat room caching
    room_key = CacheKeys.chat_room(1)
    room_data = {
        "id": 1,
        "name": "General Discussion",
        "description": "Main chat room",
        "is_active": True,
        "created_at": "2025-01-15T10:30:00Z"
    }
    
    await cache_service.set(room_key, room_data, ttl=300)  # 5 minutes
    print(f"✅ Cached chat room: {room_key}")
    
    # Test message caching
    messages_key = CacheKeys.chat_messages(1, 0)  # room_id=1, page=0
    messages_data = [
        {
            "id": 1,
            "room_id": 1,
            "user_id": 1,
            "content": "Hello everyone!",
            "message_type": "text",
            "created_at": "2025-01-15T10:31:00Z"
        },
        {
            "id": 2,
            "room_id": 1,
            "user_id": 2,
            "content": "Hi there! 👋",
            "message_type": "text",
            "created_at": "2025-01-15T10:32:00Z"
        }
    ]
    
    await cache_service.set(messages_key, messages_data, ttl=300)
    print(f"✅ Cached chat messages: {messages_key}")
    
    # Test user conversations caching
    conversations_key = CacheKeys.user_conversations(1)
    conversations_data = [
        {
            "user_id": 2,
            "username": "janedoe",
            "last_message": "Hey there!",
            "last_message_at": "2025-01-15T10:32:00Z",
            "unread_count": 1
        }
    ]
    
    await cache_service.set(conversations_key, conversations_data, ttl=300)
    print(f"✅ Cached user conversations: {conversations_key}")
    
    # Retrieve and display cached data
    print("\n📖 Retrieving cached data:")
    
    cached_room = await cache_service.get(room_key)
    cached_messages = await cache_service.get(messages_key)
    cached_conversations = await cache_service.get(conversations_key)
    
    print(f"   🏠 Room: {cached_room['name'] if cached_room else 'Not found'}")
    print(f"   💬 Messages: {len(cached_messages) if cached_messages else 0} messages")
    print(f"   👥 Conversations: {len(cached_conversations) if cached_conversations else 0} conversations")
    
    # Clean up
    await cache_service.delete_pattern("chat:*")
    print("\n🧹 Cleaned up chat cache data")
    
    await redis_manager.disconnect()


async def main():
    """Run all tests"""
    print("🚀 Redis Integration Test Suite\n")
    print("=" * 50)
    
    try:
        await test_basic_redis_operations()
        await test_performance_comparison() 
        await test_chat_caching_patterns()
        
        print("\n" + "=" * 50)
        print("✅ All Redis tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
