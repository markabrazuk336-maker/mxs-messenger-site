import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt

from app.database import Base, engine, SessionLocal
from app.models import User
from app.routers import chats, messages, users
from app.websocket import manager

load_dotenv()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MXS Messenger", version="0.7.0")

origin = os.getenv("FRONTEND_ORIGIN", "*")
allow_origins = ["*"] if origin == "*" else [origin]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BASE_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
DATA_DIR = PROJECT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

app.include_router(users.router)
app.include_router(chats.router)
app.include_router(messages.router)


@app.get("/api/health")
def health():
    return {"name": "MXS", "status": "ok", "version": "0.7.0"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    db = SessionLocal()
    user_id = None
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY", "dev_secret"), algorithms=["HS256"])
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.close(code=1008)
            return
        user.status = "online"
        user.last_seen_at = datetime.utcnow()
        db.commit()
    except (JWTError, TypeError, ValueError):
        await websocket.close(code=1008)
        return
    finally:
        db.close()

    await manager.connect(user_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            if raw.startswith("typing:"):
                try:
                    chat_id = int(raw.split(":", 1)[1])
                    await manager.broadcast_typing(user_id, chat_id)
                except Exception:
                    pass
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.status = "offline"
                user.last_seen_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()


# ВАЖНО: static frontend монтируется последним, чтобы не перехватывать /api и /ws.
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
