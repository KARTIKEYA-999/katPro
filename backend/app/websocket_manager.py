import json
import logging
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket

logger = logging.getLogger("sih_procurement.websocket")

class ConnectionManager:
    def __init__(self):
        # All connected clients
        self.all_connections: Set[WebSocket] = set()
        # center_id -> Set[WebSocket]
        self.center_rooms: Dict[int, Set[WebSocket]] = {}
        # user_id -> Set[WebSocket]
        self.user_rooms: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: Optional[int] = None, center_id: Optional[int] = None):
        await websocket.accept()
        self.all_connections.add(websocket)

        if center_id is not None:
            if center_id not in self.center_rooms:
                self.center_rooms[center_id] = set()
            self.center_rooms[center_id].add(websocket)

        if user_id is not None:
            if user_id not in self.user_rooms:
                self.user_rooms[user_id] = set()
            self.user_rooms[user_id].add(websocket)

        logger.info(f"WebSocket connected. User: {user_id}, Center: {center_id}. Total active: {len(self.all_connections)}")

    def disconnect(self, websocket: WebSocket, user_id: Optional[int] = None, center_id: Optional[int] = None):
        self.all_connections.discard(websocket)

        if center_id is not None and center_id in self.center_rooms:
            self.center_rooms[center_id].discard(websocket)
            if not self.center_rooms[center_id]:
                del self.center_rooms[center_id]

        if user_id is not None and user_id in self.user_rooms:
            self.user_rooms[user_id].discard(websocket)
            if not self.user_rooms[user_id]:
                del self.user_rooms[user_id]

        logger.info(f"WebSocket disconnected. Remaining total: {len(self.all_connections)}")

    async def broadcast_to_center(self, center_id: int, message: Dict[str, Any]):
        """Broadcasts event to all farmers and officials tuned to a specific procurement center"""
        if center_id in self.center_rooms:
            payload = json.dumps(message)
            dead_sockets = []
            for connection in list(self.center_rooms[center_id]):
                try:
                    await connection.send_text(payload)
                except Exception:
                    dead_sockets.append(connection)
            for dead in dead_sockets:
                self.disconnect(dead, center_id=center_id)

    async def send_to_user(self, user_id: int, message: Dict[str, Any]):
        """Sends targeted personal notification to a specific farmer or official"""
        if user_id in self.user_rooms:
            payload = json.dumps(message)
            dead_sockets = []
            for connection in list(self.user_rooms[user_id]):
                try:
                    await connection.send_text(payload)
                except Exception:
                    dead_sockets.append(connection)
            for dead in dead_sockets:
                self.disconnect(dead, user_id=user_id)

    async def broadcast_all(self, message: Dict[str, Any]):
        """Broadcasts system-wide notification"""
        payload = json.dumps(message)
        dead_sockets = []
        for connection in list(self.all_connections):
            try:
                await connection.send_text(payload)
            except Exception:
                dead_sockets.append(connection)
        for dead in dead_sockets:
            self.all_connections.discard(dead)

manager = ConnectionManager()
