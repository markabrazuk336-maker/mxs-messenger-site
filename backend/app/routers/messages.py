import os
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ChatMember, ChatRead, Message, User
from app.schemas import MessageCreate, MessageEdit, MessageOut
from app.websocket import manager

router = APIRouter(prefix="/api/messages", tags=["messages"])
last_send_time: dict[int, float] = defaultdict(lambda: 0.0)
minute_bucket: dict[int, deque[float]] = defaultdict(deque)

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/heic", "image/heif"}
MAX_IMAGE_SIZE = 8 * 1024 * 1024


def is_chat_member(db: Session, chat_id: int, user_id: int) -> bool:
    return db.query(ChatMember).filter(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id).first() is not None


def get_chat_members(db: Session, chat_id: int) -> list[int]:
    return [m.user_id for m in db.query(ChatMember).filter(ChatMember.chat_id == chat_id).all()]


def msg_to_dict(msg: Message) -> dict:
    return {
        "id": msg.id,
        "chat_id": msg.chat_id,
        "sender_id": msg.sender_id,
        "text": msg.text or "",
        "message_type": msg.message_type,
        "file_url": msg.file_url or "",
        "file_name": msg.file_name or "",
        "file_mime": msg.file_mime or "",
        "file_size": msg.file_size or 0,
        "is_deleted": msg.is_deleted,
        "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
        "created_at": msg.created_at.isoformat(),
    }


def rate_limit(user_id: int):
    now = time.time()
    if now - last_send_time[user_id] < 0.45:
        raise HTTPException(status_code=429, detail="Слишком часто. Подожди немного")
    bucket = minute_bucket[user_id]
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= 45:
        raise HTTPException(status_code=429, detail="Слишком много сообщений за минуту")
    last_send_time[user_id] = now
    bucket.append(now)


def mark_read(db: Session, chat_id: int, user_id: int):
    last = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.id.desc()).first()
    if not last:
        return
    row = db.query(ChatRead).filter(ChatRead.chat_id == chat_id, ChatRead.user_id == user_id).first()
    if not row:
        row = ChatRead(chat_id=chat_id, user_id=user_id, last_read_message_id=last.id)
        db.add(row)
    else:
        row.last_read_message_id = max(row.last_read_message_id, last.id)
    db.commit()


@router.get("/{chat_id}", response_model=list[MessageOut])
def get_messages(chat_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not is_chat_member(db, chat_id, current_user.id):
        raise HTTPException(status_code=403, detail="Нет доступа к чату")
    messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.asc()).limit(300).all()
    mark_read(db, chat_id, current_user.id)
    return messages


@router.post("/{chat_id}", response_model=MessageOut)
async def send_message(chat_id: int, payload: MessageCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not is_chat_member(db, chat_id, current_user.id):
        raise HTTPException(status_code=403, detail="Нет доступа к чату")
    rate_limit(current_user.id)
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Сообщение пустое")
    msg = Message(chat_id=chat_id, sender_id=current_user.id, text=text, message_type="text")
    db.add(msg)
    db.commit()
    db.refresh(msg)
    data = {"type": "message", "message": msg_to_dict(msg)}
    for uid in get_chat_members(db, chat_id):
        await manager.send_to_user(uid, data)
    return msg


@router.post("/{chat_id}/image", response_model=MessageOut)
async def upload_image(chat_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not is_chat_member(db, chat_id, current_user.id):
        raise HTTPException(status_code=403, detail="Нет доступа к чату")
    rate_limit(current_user.id)
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Можно отправлять только JPG, PNG, WEBP, GIF, HEIC/HEIF")
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Картинка слишком большая. Максимум 8 МБ")
    ext = os.path.splitext(file.filename or "image.jpg")[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"]:
        ext = ".jpg" if file.content_type == "image/jpeg" else ".png"
    safe_name = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / safe_name
    path.write_bytes(content)
    msg = Message(
        chat_id=chat_id,
        sender_id=current_user.id,
        text="",
        message_type="image",
        file_url=f"/uploads/{safe_name}",
        file_name=file.filename or safe_name,
        file_mime=file.content_type or "image/jpeg",
        file_size=len(content),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    data = {"type": "message", "message": msg_to_dict(msg)}
    for uid in get_chat_members(db, chat_id):
        await manager.send_to_user(uid, data)
    return msg


@router.patch("/{message_id}", response_model=MessageOut)
async def edit_message(message_id: int, payload: MessageEdit, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg or msg.sender_id != current_user.id:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    if msg.message_type != "text":
        raise HTTPException(status_code=400, detail="Можно редактировать только текст")
    msg.text = payload.text.strip()
    msg.edited_at = datetime.utcnow()
    db.commit()
    db.refresh(msg)
    data = {"type": "message_updated", "message": msg_to_dict(msg)}
    for uid in get_chat_members(db, msg.chat_id):
        await manager.send_to_user(uid, data)
    return msg


@router.delete("/{message_id}", response_model=MessageOut)
async def delete_message(message_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg or msg.sender_id != current_user.id:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    msg.is_deleted = True
    msg.text = "Сообщение удалено"
    msg.file_url = ""
    db.commit()
    db.refresh(msg)
    data = {"type": "message_updated", "message": msg_to_dict(msg)}
    for uid in get_chat_members(db, msg.chat_id):
        await manager.send_to_user(uid, data)
    return msg
