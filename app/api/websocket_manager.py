from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect


class ConnectionManager:
    def __init__(self):
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.connections.discard(websocket)

    async def send(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
        except (WebSocketDisconnect, RuntimeError):
            self.disconnect(websocket)
            raise WebSocketDisconnect(code=1006)