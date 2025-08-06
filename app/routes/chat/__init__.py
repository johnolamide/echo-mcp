from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Header
from sqlmodel import Session

from app.database.connection import get_session
from app.models.chat import (
    ChatRoomCreate, ChatRoomRead, ChatMessageCreate, 
    ChatMessageRead, WebSocketMessage, DirectMessageCreate, 
    DirectMessageRead, ConversationRead
)
from app.models.user import User
from app.services.chat import ChatService, message_to_read
from app.services.auth import AuthService
from app.core.auth_dependency import get_current_user

router = APIRouter()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: int):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: int):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_room(self, message: str, room_id: int):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_text(message)
                except:
                    # Remove disconnected connections
                    self.active_connections[room_id].remove(connection)

manager = ConnectionManager()


@router.post("/rooms", response_model=ChatRoomRead, status_code=status.HTTP_201_CREATED)
async def create_chat_room(
    room_data: ChatRoomCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new chat room"""
    chat_service = ChatService(session)
    room = chat_service.create_chat_room(room_data, current_user.id)
    return room


@router.get("/rooms", response_model=List[ChatRoomRead])
async def get_chat_rooms(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """Get all chat rooms"""
    chat_service = ChatService(session)
    rooms = chat_service.get_chat_rooms(skip=skip, limit=limit)
    return rooms


@router.get("/rooms/{room_id}", response_model=ChatRoomRead)
async def get_chat_room(
    room_id: int,
    session: Session = Depends(get_session)
):
    """Get chat room by ID"""
    chat_service = ChatService(session)
    room = chat_service.get_chat_room(room_id)
    
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found"
        )
    
    return room


@router.get("/rooms/{room_id}/messages", response_model=List[ChatMessageRead])
async def get_chat_messages(
    room_id: int,
    skip: int = 0,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """Get messages from a chat room"""
    chat_service = ChatService(session)
    messages = chat_service.get_chat_messages(room_id, skip=skip, limit=limit)
    # Convert to ChatMessageRead objects
    return [message_to_read(msg) for msg in messages]


@router.post("/rooms/{room_id}/messages", response_model=ChatMessageRead)
async def send_chat_message(
    room_id: int,
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Send a message to a chat room (REST endpoint)"""
    chat_service = ChatService(session)
    
    # Ensure message is for the correct room
    message_data.room_id = room_id
    message = chat_service.create_chat_message(message_data, current_user.id)
    
    # Broadcast to WebSocket connections
    ws_message = WebSocketMessage(
        type="message",
        room_id=room_id,
        content=message.content,
        message_metadata={"user_id": current_user.id, "username": current_user.username, "message_id": message.id}
    )
    
    await manager.broadcast_to_room(ws_message.model_dump_json(), room_id)
    
    # Return ChatMessageRead object
    return message_to_read(message)


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: int,
    token: str = None,
    session: Session = Depends(get_session)
):
    """WebSocket endpoint for real-time chat"""
    # Validate auth token
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return
    
    auth_service = AuthService(session)
    user = auth_service.validate_session(token)
    
    if not user:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    # Verify room exists
    chat_service = ChatService(session)
    room = chat_service.get_chat_room(room_id)
    
    if not room:
        await websocket.close(code=1008, reason="Room not found")
        return
    
    await manager.connect(websocket, room_id)
    
    # Send join notification
    join_message = WebSocketMessage(
        type="join",
        room_id=room_id,
        content=f"{user.username} joined the room",
        message_metadata={"user_id": user.id, "username": user.username}
    )
    
    await manager.broadcast_to_room(join_message.model_dump_json(), room_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                ws_message = WebSocketMessage.model_validate_json(data)
                
                if ws_message.type == "message" and ws_message.content:
                    # Create message in database
                    message_data = ChatMessageCreate(
                        room_id=room_id,
                        content=ws_message.content,
                        message_metadata=ws_message.message_metadata
                    )
                    
                    message = chat_service.create_chat_message(message_data, user.id)
                    
                    # Broadcast to all connections in the room
                    broadcast_message = WebSocketMessage(
                        type="message",
                        room_id=room_id,
                        content=message.content,
                        message_metadata={
                            "user_id": user.id,
                            "username": user.username,
                            "message_id": message.id,
                            "created_at": message.created_at.isoformat()
                        }
                    )
                    
                    await manager.broadcast_to_room(broadcast_message.model_dump_json(), room_id)
                
            except Exception as e:
                error_message = WebSocketMessage(
                    type="error",
                    content=f"Invalid message format: {str(e)}"
                )
                await manager.send_personal_message(error_message.model_dump_json(), websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        
        # Send leave notification
        leave_message = WebSocketMessage(
            type="leave",
            room_id=room_id,
            content=f"{user.username} left the room",
            message_metadata={"user_id": user.id, "username": user.username}
        )
        
        await manager.broadcast_to_room(leave_message.model_dump_json(), room_id)


# Direct Messaging Endpoints

@router.post("/direct/send", response_model=DirectMessageRead, status_code=status.HTTP_201_CREATED)
async def send_direct_message(
    dm_data: DirectMessageCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Send a direct message to a specific user"""
    # Can't send message to yourself
    if dm_data.recipient_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send direct message to yourself"
        )
    
    chat_service = ChatService(session)
    
    try:
        direct_message = chat_service.send_direct_message(dm_data, current_user.id)
        
        # Broadcast to WebSocket connections (both sender and recipient)
        ws_message = WebSocketMessage(
            type="direct_message",
            room_id=direct_message.room_id,
            content=direct_message.content,
            message_metadata={
                "sender_id": current_user.id,
                "sender_username": current_user.username,
                "recipient_id": dm_data.recipient_user_id,
                "message_id": direct_message.id
            }
        )
        
        # Broadcast to the direct message room
        await manager.broadcast_to_room(ws_message.model_dump_json(), direct_message.room_id)
        
        return direct_message
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/conversations", response_model=List[ConversationRead])
async def get_user_conversations(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all conversations (direct message threads) for the current user"""
    chat_service = ChatService(session)
    conversations = chat_service.get_user_conversations(current_user.id)
    return conversations


@router.get("/direct/{user_id}/messages", response_model=List[DirectMessageRead])
async def get_direct_messages_with_user(
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get direct message history with a specific user"""
    # Can't get messages with yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot get direct messages with yourself"
        )
    
    chat_service = ChatService(session)
    messages = chat_service.get_direct_messages_with_user(
        current_user.id, user_id, skip, limit
    )
    return messages
