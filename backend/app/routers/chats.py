from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import get_current_user, normalize_email, normalize_phone, normalize_username
from app.database import get_db
from app.models import Chat, ChatMember, ChatRead, Message, User
from app.schemas import ChatCreate, ChatOut, GroupCreate

router = APIRouter(prefix="/api/chats", tags=["chats"])


def user_in_chat(db: Session, chat_id: int, user_id: int) -> bool:
    return db.query(ChatMember).filter(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id).first() is not None


def find_existing_private_chat(db: Session, user_a: int, user_b: int):
    chats_a = db.query(ChatMember.chat_id).filter(ChatMember.user_id == user_a).subquery()
    return db.query(Chat).join(ChatMember, Chat.id == ChatMember.chat_id).filter(Chat.type == "private", Chat.id.in_(chats_a), ChatMember.user_id == user_b).first()


def find_user_for_private_chat(db: Session, target: str) -> User | None:
    raw = target.strip()
    if not raw:
        return None
    username = normalize_username(raw)
    phone = None
    try:
        phone = normalize_phone(raw)
    except HTTPException:
        phone = None
    email = None
    if "@" in raw and not raw.startswith("@"):
        try:
            email = normalize_email(raw)
        except HTTPException:
            email = None
    digits = "".join(ch for ch in raw if ch.isdigit())
    conditions = [User.username == username]
    if phone:
        conditions.append(User.phone == phone)
    if email:
        conditions.append(User.email == email)
    if digits and len(digits) == 8:
        conditions.append(User.mxs_number == digits)
    return db.query(User).filter(or_(*conditions)).first()


def chat_to_out(db: Session, chat: Chat, current_user_id: int) -> ChatOut:
    other = None
    if chat.type == "private":
        other_member = db.query(ChatMember).filter(ChatMember.chat_id == chat.id, ChatMember.user_id != current_user_id).first()
        if other_member:
            other = db.query(User).filter(User.id == other_member.user_id).first()
    last = db.query(Message).filter(Message.chat_id == chat.id).order_by(Message.created_at.desc()).first()
    read = db.query(ChatRead).filter(ChatRead.chat_id == chat.id, ChatRead.user_id == current_user_id).first()
    last_read_id = read.last_read_message_id if read else 0
    unread = db.query(Message).filter(Message.chat_id == chat.id, Message.id > last_read_id, Message.sender_id != current_user_id).count()
    members_count = db.query(ChatMember).filter(ChatMember.chat_id == chat.id).count()
    title = chat.title
    avatar_url = chat.avatar_url or ""
    if chat.type == "private" and other:
        title = other.display_name
        avatar_url = other.avatar_url or ""
    last_text = None
    last_type = None
    if last:
        last_type = last.message_type
        if last.is_deleted:
            last_text = "Сообщение удалено"
        elif last.message_type == "image":
            last_text = "Фото"
        else:
            last_text = last.text
    return ChatOut(id=chat.id, type=chat.type, title=title, avatar_url=avatar_url, other_user=other, members_count=members_count, last_message=last_text, last_message_type=last_type, last_message_at=last.created_at if last else None, unread_count=unread)


@router.get("", response_model=list[ChatOut])
def list_chats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    memberships = db.query(ChatMember).filter(ChatMember.user_id == current_user.id).all()
    chats = [db.query(Chat).filter(Chat.id == m.chat_id).first() for m in memberships]
    chats = [c for c in chats if c]
    def sort_date(chat: Chat):
        last = db.query(Message).filter(Message.chat_id == chat.id).order_by(Message.created_at.desc()).first()
        return last.created_at if last else chat.created_at
    chats.sort(key=sort_date, reverse=True)
    return [chat_to_out(db, chat, current_user.id) for chat in chats]


@router.post("", response_model=ChatOut)
def create_chat(payload: ChatCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    target_user = find_user_for_private_chat(db, payload.target)
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден. Введите точный username или телефон")
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя создать чат с самим собой")
    existing = find_existing_private_chat(db, current_user.id, target_user.id)
    if existing:
        return chat_to_out(db, existing, current_user.id)
    chat = Chat(type="private", title="")
    db.add(chat)
    db.commit()
    db.refresh(chat)
    db.add(ChatMember(chat_id=chat.id, user_id=current_user.id, role="owner"))
    db.add(ChatMember(chat_id=chat.id, user_id=target_user.id, role="member"))
    db.commit()
    return chat_to_out(db, chat, current_user.id)


@router.post("/groups", response_model=ChatOut)
def create_group(payload: GroupCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    title = payload.title.strip()
    chat = Chat(type="group", title=title)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    db.add(ChatMember(chat_id=chat.id, user_id=current_user.id, role="owner"))
    added = {current_user.id}
    for item in payload.members[:30]:
        user = find_user_for_private_chat(db, item)
        if user and user.id not in added:
            db.add(ChatMember(chat_id=chat.id, user_id=user.id, role="member"))
            added.add(user.id)
    db.commit()
    return chat_to_out(db, chat, current_user.id)


@router.get("/{chat_id}", response_model=ChatOut)
def get_chat(chat_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat or not user_in_chat(db, chat_id, current_user.id):
        raise HTTPException(status_code=404, detail="Чат не найден")
    return chat_to_out(db, chat, current_user.id)
