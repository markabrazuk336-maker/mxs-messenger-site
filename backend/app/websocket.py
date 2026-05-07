from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active: dict[int, list[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self.active and websocket in self.active[user_id]:
            self.active[user_id].remove(websocket)
        if user_id in self.active and not self.active[user_id]:
            del self.active[user_id]

    async def send_to_user(self, user_id: int, data: dict):
        for ws in list(self.active.get(user_id, [])):
            try:
                await ws.send_json(data)
            except Exception:
                pass

    async def broadcast_typing(self, user_id: int, chat_id: int):
        data = {"type": "typing", "chat_id": chat_id, "user_id": user_id}
        for uid, sockets in list(self.active.items()):
            if uid == user_id:
                continue
            for ws in list(sockets):
                try:
                    await ws.send_json(data)
                except Exception:
                    pass

manager = ConnectionManager()
