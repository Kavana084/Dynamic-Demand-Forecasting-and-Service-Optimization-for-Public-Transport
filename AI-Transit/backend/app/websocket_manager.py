from fastapi import WebSocket
from typing import List
import json
import logging
from .services.vehicle_tracking_service import vehicle_tracking_service

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.total_disconnects = 0

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.total_disconnects += 1

    async def handle_message(self, websocket: WebSocket, text: str):
        try:
            data = json.loads(text)
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
        except json.JSONDecodeError:
            pass

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: dict):
        # Clean up dead connections during broadcast
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                dead_connections.append(connection)
                
        for dead in dead_connections:
            self.disconnect(dead)

    def get_metrics(self) -> dict:
        return {
            "active_connections": len(self.active_connections),
            "total_disconnects": self.total_disconnects,
            "active_vehicle_streams": len(vehicle_tracking_service.active_vehicles)
        }

manager = ConnectionManager()
