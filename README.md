# Echo MCP

**Echo MCP** is a comprehensive multi-service platform built with FastAPI that provides chat, food ordering, ride booking, and user management services. The platform is designed with a modular architecture that supports both REST APIs and WebSocket connections for real-time communication.

## 🚀 Features

- **🔐 User Registration & Authentication**: Email-based authentication with Redis session caching
- **💬 Real-time Chat Service**: WebSocket-powered group chat AND direct messaging with Redis caching
- **🍕 Food Ordering Service**: Restaurant search and food ordering with intelligent API response caching
- **🚗 Ride Booking Service**: Ride booking and fare estimation with cached external API support
- **⚡ Redis Integration**: Lightning-fast data retrieval with comprehensive caching layer
- **📊 Modular Architecture**: Clean separation with SQLModel (SQLAlchemy + Pydantic)
- **🗄️ Database Flexibility**: SQLite by default, easily configurable for PostgreSQL, MySQL
- **🚀 High Performance**: 10-100x faster data access with Redis caching

## 📁 Project Structure

```
echo-mcp/
├── main.py                     # 🎯 FastAPI application entry point
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # ⚙️ Application configuration & settings
│   ├── database/
│   │   ├── __init__.py
│   │   └── connection.py       # 🔌 Database connection & session management
│   ├── models/                 # 📋 SQLModel data models
│   │   ├── auth/
│   │   │   └── __init__.py     # 🔐 Authentication & session models
│   │   ├── chat/
│   │   │   └── __init__.py     # 💬 Chat rooms & message models
│   │   ├── food/
│   │   │   └── __init__.py     # 🍕 Food orders & restaurant models
│   │   ├── ride/
│   │   │   └── __init__.py     # 🚗 Ride bookings & fare models
│   │   └── user/
│   │       └── __init__.py     # 👤 User registration & profile models
│   ├── routes/                 # 🛣️ FastAPI API endpoints
│   │   ├── auth/
│   │   │   └── __init__.py     # 🔐 Authentication routes
│   │   ├── chat/
│   │   │   └── __init__.py     # 💬 Chat routes (REST + WebSocket)
│   │   ├── food/
│   │   │   └── __init__.py     # 🍕 Food service routes
│   │   ├── ride/
│   │   │   └── __init__.py     # 🚗 Ride service routes
│   │   └── user/
│   │       └── __init__.py     # 👤 User management routes
│   └── services/               # 🔧 Business logic layer
│       ├── auth/
│       │   └── __init__.py     # 🔐 Authentication business logic
│       ├── chat/
│       │   └── __init__.py     # 💬 Chat service logic
│       ├── food/
│       │   └── __init__.py     # 🍕 Food service with external API integration
│       ├── ride/
│       │   └── __init__.py     # 🚗 Ride service with external API integration
│       └── user/
│           └── __init__.py     # 👤 User service logic
├── requirements.txt            # 📦 Python dependencies
├── .env.example               # 🔧 Environment variables template
└── README.md                  # 📖 This documentation
```

### 📂 Folder Descriptions

- **`app/core/`**: Core application configuration, settings, and global utilities
- **`app/database/`**: Database connection management, session handling, and initialization
- **`app/models/`**: SQLModel data models defining database schemas and API contracts
- **`app/routes/`**: FastAPI route definitions handling HTTP requests and WebSocket connections
- **`app/services/`**: Business logic layer containing service classes for each feature

## 🛠️ Setup Instructions

### 1. Environment Setup
```bash
# Activate your virtual environment (already created with uv)
source .venv/bin/activate

# Install dependencies (if not already installed)
uv pip install httpx
```

### 2. Configuration
```bash
# Create environment file from template
cp .env.example .env

# Edit .env with your configuration
# - Update SECRET_KEY for production
# - Configure external API credentials if available
```

### 3. Run the Application
```bash
# Start the development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Access Points
- **🌐 API Documentation**: http://localhost:8000/docs
- **📚 Alternative Docs**: http://localhost:8000/redoc
- **❤️ Health Check**: http://localhost:8000/health
- **🏠 Root Endpoint**: http://localhost:8000/

---

# 📚 API Services Documentation

## 👤 User Registration Service

**Purpose**: Handles user registration with username, email, and basic profile information.

### Register New User

**Endpoint**: `POST /api/v1/users/register`

**Request Body**:
```json
{
  "username": "johndoe",
  "firstname": "John",
  "lastname": "Doe", 
  "email": "john.doe@example.com"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "username": "johndoe",
  "firstname": "John",
  "lastname": "Doe",
  "email": "john.doe@example.com",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Demo cURL**:
```bash
curl -X POST "http://localhost:8000/api/v1/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "firstname": "John",
    "lastname": "Doe",
    "email": "john.doe@example.com"
  }'
```

### Get User Profile

**Endpoint**: `GET /api/v1/users/{user_id}`

**Response** (200 OK):
```json
{
  "id": 1,
  "username": "johndoe",
  "firstname": "John",
  "lastname": "Doe",
  "email": "john.doe@example.com",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

## 🔐 Authentication Service

**Purpose**: Manages user authentication using email-based login with session tokens.

### Login

**Endpoint**: `POST /api/v1/auth/login`

**Request Body**:
```json
{
  "email": "john.doe@example.com"
}
```

**Response** (200 OK):
```json
{
  "access_token": "s0YKKdM0P3rJopllHjtikigfMyk2mB0zocrs5hUyIAM",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Demo cURL**:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com"
  }'
```

### Get Current User

**Endpoint**: `GET /api/v1/auth/me`

**Headers**: `Authorization: Bearer {access_token}`

**Response** (200 OK):
```json
{
  "id": 1,
  "username": "johndoe",
  "firstname": "John",
  "lastname": "Doe",
  "email": "john.doe@example.com",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

### Logout

**Endpoint**: `POST /api/v1/auth/logout`

**Headers**: `Authorization: Bearer {access_token}`

**Response** (200 OK):
```json
{
  "message": "Logged out successfully"
}
```

---

## 💬 Chat Service

**Purpose**: Provides real-time chat functionality with both **group chat rooms** and **direct messaging** between users, featuring persistent message storage and WebSocket support.

### Create Chat Room

**Endpoint**: `POST /api/v1/chat/rooms`

**Headers**: `Authorization: Bearer {access_token}`

**Request Body**:
```json
{
  "name": "General Discussion",
  "description": "A place for general conversations"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "name": "General Discussion",
  "description": "A place for general conversations",
  "is_active": true,
  "created_by": 1,
  "created_at": "2025-01-15T10:35:00Z"
}
```

**Demo cURL**:
```bash
curl -X POST "http://localhost:8000/api/v1/chat/rooms" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "General Discussion",
    "description": "A place for general conversations"
  }'
```

### Send Message (REST)

**Endpoint**: `POST /api/v1/chat/rooms/{room_id}/messages`

**Headers**: `Authorization: Bearer {access_token}`

**Request Body**:
```json
{
  "room_id": 1,
  "content": "Hello everyone! 👋",
  "message_type": "text",
  "message_metadata": {
    "emoji": true
  }
}
```

**Response** (200 OK):
```json
{
  "id": 1,
  "room_id": 1,
  "user_id": 1,
  "content": "Hello everyone! 👋",
  "message_type": "text",
  "message_metadata": {
    "emoji": true
  },
  "created_at": "2025-01-15T10:40:00Z"
}
```

### Get Chat Messages

**Endpoint**: `GET /api/v1/chat/rooms/{room_id}/messages?skip=0&limit=50`

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "room_id": 1,
    "user_id": 1,
    "content": "Hello everyone! 👋",
    "message_type": "text",
    "message_metadata": {
      "emoji": true
    },
    "created_at": "2025-01-15T10:40:00Z"
  }
]
```

### WebSocket Connection

**Endpoint**: `WS /api/v1/chat/ws/{room_id}?token={access_token}`

**JavaScript Example**:
```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/api/v1/chat/ws/1?token=YOUR_TOKEN');

// Send message
ws.send(JSON.stringify({
  type: "message",
  content: "Hello from WebSocket!",
  metadata: { "source": "web" }
}));

// Receive messages
ws.onmessage = function(event) {
  const message = JSON.parse(event.data);
  console.log('Message received:', message);
};

// Message types: "message", "join", "leave", "error"
```

**WebSocket Message Format**:
```json
{
  "type": "message",
  "room_id": 1,
  "content": "Hello from WebSocket!",
  "metadata": {
    "user_id": 1,
    "username": "johndoe",
    "message_id": 2,
    "created_at": "2025-01-15T10:45:00Z"
  }
}
```

### Direct Messaging

The chat service also supports **direct messaging** between users for private one-on-one conversations.

### Send Direct Message

**Endpoint**: `POST /api/v1/chat/direct/send`

**Headers**: `Authorization: Bearer {access_token}`

**Request Body**:
```json
{
  "recipient_user_id": 2,
  "content": "Hey there! How are you doing?",
  "message_type": "text",
  "message_metadata": {
    "priority": "normal"
  }
}
```

**Response** (200 OK):
```json
{
  "id": 15,
  "sender_user_id": 1,
  "recipient_user_id": 2,
  "content": "Hey there! How are you doing?",
  "message_type": "text",
  "message_metadata": {
    "priority": "normal"
  },
  "is_read": false,
  "created_at": "2025-01-15T12:00:00Z"
}
```

### Get Conversations

**Endpoint**: `GET /api/v1/chat/conversations?skip=0&limit=20`

**Headers**: `Authorization: Bearer {access_token}`

**Response** (200 OK):
```json
[
  {
    "user_id": 2,
    "username": "janedoe",
    "firstname": "Jane",
    "lastname": "Doe",
    "last_message": "Hey there! How are you doing?",
    "last_message_at": "2025-01-15T12:00:00Z",
    "unread_count": 1
  },
  {
    "user_id": 3,
    "username": "bobsmith",
    "firstname": "Bob",
    "lastname": "Smith", 
    "last_message": "Thanks for the help!",
    "last_message_at": "2025-01-15T11:30:00Z",
    "unread_count": 0
  }
]
```

### Get Direct Messages

**Endpoint**: `GET /api/v1/chat/direct/{user_id}/messages?skip=0&limit=50`

**Headers**: `Authorization: Bearer {access_token}`

**Response** (200 OK):
```json
[
  {
    "id": 15,
    "sender_user_id": 1,
    "recipient_user_id": 2,
    "content": "Hey there! How are you doing?",
    "message_type": "text",
    "message_metadata": {
      "priority": "normal"
    },
    "is_read": false,
    "created_at": "2025-01-15T12:00:00Z"
  },
  {
    "id": 14,
    "sender_user_id": 2,
    "recipient_user_id": 1,
    "content": "Hi! I'm doing great, thanks for asking.",
    "message_type": "text",
    "message_metadata": {},
    "is_read": true,
    "created_at": "2025-01-15T11:58:00Z"
  }
]
```

### Direct Message WebSocket

**Endpoint**: `WS /api/v1/chat/direct/ws?token={access_token}`

**JavaScript Example**:
```javascript
// Connect to direct message WebSocket
const directWs = new WebSocket('ws://localhost:8000/api/v1/chat/direct/ws?token=YOUR_TOKEN');

// Send direct message
directWs.send(JSON.stringify({
  type: "direct_message",
  recipient_user_id: 2,
  content: "Quick message via WebSocket!",
  metadata: { "urgent": true }
}));

// Receive direct messages
directWs.onmessage = function(event) {
  const message = JSON.parse(event.data);
  console.log('Direct message received:', message);
};
```

**Demo cURL for Direct Message**:
```bash
curl -X POST "http://localhost:8000/api/v1/chat/direct/send" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_user_id": 2,
    "content": "Hey there! How are you doing?",
    "message_type": "text"
  }'
```

---

## 🍕 Food Service

**Purpose**: Handles restaurant search, food ordering, and order management with support for external food delivery APIs.

### Search Restaurants

**Endpoint**: `POST /api/v1/food/search-restaurants`

**Request Body**:
```json
{
  "query": "pizza",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "cuisine_type": "Italian",
  "price_range": "$$"
}
```

**Response** (200 OK):
```json
[
  {
    "id": "rest_1",
    "name": "Pizza Palace",
    "cuisine_type": "Italian",
    "rating": 4.5,
    "price_range": "$$",
    "delivery_time": "30-45 min",
    "image_url": "https://example.com/pizza.jpg"
  },
  {
    "id": "rest_2", 
    "name": "Mario's Pizzeria",
    "cuisine_type": "Italian",
    "rating": 4.2,
    "price_range": "$",
    "delivery_time": "25-35 min",
    "image_url": "https://example.com/marios.jpg"
  }
]
```

**Demo cURL**:
```bash
curl -X POST "http://localhost:8000/api/v1/food/search-restaurants" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "pizza",
    "cuisine_type": "Italian"
  }'
```

### Create Food Order

**Endpoint**: `POST /api/v1/food/orders`

**Headers**: `Authorization: Bearer {access_token}`

**Request Body**:
```json
{
  "restaurant_id": "rest_1",
  "restaurant_name": "Pizza Palace",
  "items": [
    {
      "name": "Margherita Pizza",
      "quantity": 1,
      "price": 18.99,
      "customizations": ["Extra cheese"]
    },
    {
      "name": "Coca Cola",
      "quantity": 2,
      "price": 2.50
    }
  ],
  "total_amount": 23.99,
  "delivery_address": "123 Main St, New York, NY 10001",
  "phone_number": "+1-555-123-4567"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "user_id": 1,
  "restaurant_id": "rest_1",
  "restaurant_name": "Pizza Palace",
  "items": [
    {
      "name": "Margherita Pizza",
      "quantity": 1,
      "price": 18.99,
      "customizations": ["Extra cheese"]
    },
    {
      "name": "Coca Cola",
      "quantity": 2,
      "price": 2.50
    }
  ],
  "total_amount": 23.99,
  "delivery_address": "123 Main St, New York, NY 10001",
  "phone_number": "+1-555-123-4567",
  "status": "pending",
  "created_at": "2025-01-15T11:00:00Z"
}
```

### Get User Orders

**Endpoint**: `GET /api/v1/food/orders?skip=0&limit=20`

**Headers**: `Authorization: Bearer {access_token}`

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "restaurant_name": "Pizza Palace",
    "total_amount": 23.99,
    "status": "delivered",
    "created_at": "2025-01-15T11:00:00Z",
    "actual_delivery_time": "2025-01-15T11:35:00Z"
  }
]
```

---

## 🚗 Ride Service

**Purpose**: Provides ride booking functionality with fare estimation, supporting various ride types and external ride-hailing API integration.

### Get Fare Estimate

**Endpoint**: `POST /api/v1/ride/fare-estimate`

**Request Body**:
```json
{
  "pickup_latitude": 40.7128,
  "pickup_longitude": -74.0060,
  "destination_latitude": 40.7589,
  "destination_longitude": -73.9851,
  "ride_type": "economy"
}
```

**Response** (200 OK):
```json
{
  "ride_type": "economy",
  "estimated_fare": 11.13,
  "estimated_duration": "10 minutes",
  "estimated_distance": "5.4 km"
}
```

**Demo cURL**:
```bash
curl -X POST "http://localhost:8000/api/v1/ride/fare-estimate" \
  -H "Content-Type: application/json" \
  -d '{
    "pickup_latitude": 40.7128,
    "pickup_longitude": -74.0060, 
    "destination_latitude": 40.7589,
    "destination_longitude": -73.9851,
    "ride_type": "economy"
  }'
```

### Create Ride Booking

**Endpoint**: `POST /api/v1/ride/bookings`

**Headers**: `Authorization: Bearer {access_token}`

**Request Body**:
```json
{
  "pickup_latitude": 40.7128,
  "pickup_longitude": -74.0060,
  "pickup_address": "Times Square, New York, NY",
  "destination_latitude": 40.7589,
  "destination_longitude": -73.9851,
  "destination_address": "Central Park, New York, NY",
  "ride_type": "comfort"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "user_id": 1,
  "pickup_latitude": 40.7128,
  "pickup_longitude": -74.0060,
  "pickup_address": "Times Square, New York, NY",
  "destination_latitude": 40.7589,
  "destination_longitude": -73.9851,
  "destination_address": "Central Park, New York, NY",
  "ride_type": "comfort",
  "estimated_fare": 13.36,
  "status": "pending",
  "created_at": "2025-01-15T11:30:00Z"
}
```

### Get User Ride Bookings

**Endpoint**: `GET /api/v1/ride/bookings?skip=0&limit=20`

**Headers**: `Authorization: Bearer {access_token}`

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "pickup_address": "Times Square, New York, NY",
    "destination_address": "Central Park, New York, NY",
    "ride_type": "comfort",
    "estimated_fare": 13.36,
    "actual_fare": 12.80,
    "status": "completed",
    "created_at": "2025-01-15T11:30:00Z",
    "pickup_time": "2025-01-15T11:45:00Z",
    "drop_off_time": "2025-01-15T12:05:00Z"
  }
]
```

### Ride Types
- **`economy`**: Standard affordable rides
- **`comfort`**: Mid-range comfort with more space
- **`premium`**: Luxury vehicles with premium service
- **`shared`**: Shared rides with other passengers

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file in your project root:

```env
# Database Configuration
DATABASE_URL=sqlite:///./echo_mcp.db

# Security Settings
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS Settings
ALLOWED_HOSTS=["*"]

# External Food API (Optional)
FOOD_API_BASE_URL=https://api.fooddelivery.com
FOOD_API_KEY=your_food_api_key

# External Ride API (Optional)
RIDE_API_BASE_URL=https://api.ridehailing.com
RIDE_API_KEY=your_ride_api_key

# Email Configuration (Future Use)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_FROM=noreply@echomcp.com
```

### Database Options

**SQLite (Development)**:
```env
DATABASE_URL=sqlite:///./echo_mcp.db
```

**PostgreSQL (Production)**:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/echo_mcp
```

**MySQL**:
```env
DATABASE_URL=mysql://user:password@localhost:3306/echo_mcp
```

## 🚀 Deployment

### Using Docker (Recommended)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using systemd

```ini
# /etc/systemd/system/echo-mcp.service
[Unit]
Description=Echo MCP API Server
After=network.target

[Service]
Type=exec
User=www-data
WorkingDirectory=/path/to/echo-mcp
Environment=PATH=/path/to/echo-mcp/.venv/bin
ExecStart=/path/to/echo-mcp/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/

# Run with coverage
pytest --cov=app tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

**Made with ❤️ using FastAPI, SQLModel, and modern Python practices**
