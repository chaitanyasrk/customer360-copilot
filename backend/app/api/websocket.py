"""
WebSocket handlers for real-time chat communication
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
from datetime import datetime
import uuid


class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        # Store connections by role and user_id
        self.active_connections: Dict[str, List[WebSocket]] = {
            "users": [],
            "agents": []
        }
        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, role: str, user_id: str):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        
        if role == "user":
            self.active_connections["users"].append(websocket)
        elif role == "agent":
            self.active_connections["agents"].append(websocket)
        
        self.connection_metadata[websocket] = {
            "role": role,
            "user_id": user_id,
            "connected_at": datetime.utcnow()
        }
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        metadata = self.connection_metadata.get(websocket)
        
        if metadata:
            role = metadata["role"]
            if role == "user" and websocket in self.active_connections["users"]:
                self.active_connections["users"].remove(websocket)
            elif role == "agent" and websocket in self.active_connections["agents"]:
                self.active_connections["agents"].remove(websocket)
            
            del self.connection_metadata[websocket]
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific connection"""
        await websocket.send_text(message)
    
    async def broadcast_to_agents(self, message: str):
        """Broadcast a message to all connected agents"""
        for connection in self.active_connections["agents"]:
            await connection.send_text(message)
    
    async def broadcast_to_users(self, message: str):
        """Broadcast a message to all connected users"""
        for connection in self.active_connections["users"]:
            await connection.send_text(message)
    
    async def send_to_role(self, message: str, role: str):
        """Send message to all connections of a specific role"""
        connections = self.active_connections.get(role + "s", [])
        for connection in connections:
            await connection.send_text(message)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, role: str = "user", user_id: str = "anonymous"):
    """
    WebSocket endpoint for chat communication
    
    Args:
        websocket: WebSocket connection
        role: "user" or "agent"
        user_id: User or agent identifier
    """
    await manager.connect(websocket, role, user_id)
    
    try:
        # Send welcome message
        welcome_message = {
            "message_id": str(uuid.uuid4()),
            "sender": "system",
            "content": f"Welcome! You are connected as {role}.",
            "timestamp": datetime.utcnow().isoformat(),
            "type": "system"
        }
        await manager.send_personal_message(json.dumps(welcome_message), websocket)
        
        # Listen for messages
        while True:
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                
                # Add metadata
                message_data["message_id"] = str(uuid.uuid4())
                message_data["timestamp"] = datetime.utcnow().isoformat()
                message_data["sender_role"] = role
                message_data["sender_id"] = user_id
                
                # Route message based on type
                message_type = message_data.get("type", "chat")
                
                if message_type == "chat":
                    # Broadcast to appropriate recipients
                    if role == "user":
                        # Send user messages to agents
                        await manager.broadcast_to_agents(json.dumps(message_data))
                    elif role == "agent":
                        # Send agent messages to users or other agents based on target
                        target = message_data.get("target", "users")
                        if target == "users":
                            await manager.broadcast_to_users(json.dumps(message_data))
                        else:
                            await manager.broadcast_to_agents(json.dumps(message_data))
                
                elif message_type == "case_update":
                    # Broadcast case updates to all agents
                    await manager.broadcast_to_agents(json.dumps(message_data))
                
                elif message_type == "notification":
                    # Send notification to specific role
                    target_role = message_data.get("target_role", "agents")
                    await manager.send_to_role(json.dumps(message_data), target_role)
                
                # Echo back to sender for confirmation
                confirmation = {
                    "message_id": str(uuid.uuid4()),
                    "sender": "system",
                    "content": "Message delivered",
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "confirmation",
                    "original_message_id": message_data["message_id"]
                }
                await manager.send_personal_message(json.dumps(confirmation), websocket)
                
            except json.JSONDecodeError:
                error_message = {
                    "message_id": str(uuid.uuid4()),
                    "sender": "system",
                    "content": "Invalid message format",
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "error"
                }
                await manager.send_personal_message(json.dumps(error_message), websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        
        # Notify others about disconnection
        disconnect_message = {
            "message_id": str(uuid.uuid4()),
            "sender": "system",
            "content": f"{role} {user_id} has disconnected",
            "timestamp": datetime.utcnow().isoformat(),
            "type": "system"
        }
        
        if role == "user":
            await manager.broadcast_to_agents(json.dumps(disconnect_message))
        elif role == "agent":
            await manager.broadcast_to_agents(json.dumps(disconnect_message))
