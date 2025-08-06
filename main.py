from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.database.connection import create_db_and_tables
from app.core.redis import redis_manager
from app.routes import auth, chat, food, ride, user


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Echo MCP...")
    create_db_and_tables()
    
    # Initialize Redis connection
    await redis_manager.connect()
    
    print("✅ Echo MCP started successfully")
    yield
    
    # Shutdown
    print("🔄 Shutting down Echo MCP...")
    await redis_manager.disconnect()
    print("👋 Echo MCP shut down gracefully")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Echo MCP - Multi-service platform with chat, food, and ride services",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(food.router, prefix="/api/v1/food", tags=["Food"])
app.include_router(ride.router, prefix="/api/v1/ride", tags=["Ride"])

@app.get("/")
async def root():
    return {"message": "Welcome to Echo MCP API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Echo MCP - Multi-service platform with chat, food, and ride services",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your Bearer token (e.g., 'your_token_here')"
        }
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)