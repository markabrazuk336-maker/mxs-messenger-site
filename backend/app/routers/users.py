from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    generate_mxs_number,
    get_current_user,
    hash_password,
    normalize_email,
    normalize_login,
    normalize_phone,
    validate_username,
    verify_password,
)
from app.database import get_db
from app.models import User
from app.schemas import ProfileUpdate, TokenOut, UserLogin, UserOut, UserRegister

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/register", response_model=TokenOut)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    username = validate_username(payload.username)
    email = normalize_email(payload.email)
    phone = normalize_phone(payload.phone, required=True)
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Такой username уже занят")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Такой email уже зарегистрирован")
    if db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=400, detail="Такой номер телефона уже зарегистрирован")
    user = User(mxs_number=generate_mxs_number(db), username=username, email=email, phone=phone, display_name=payload.display_name.strip(), password_hash=hash_password(payload.password), status="online", last_seen_at=datetime.utcnow())
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    login_value = normalize_login(payload.login)
    user = db.query(User).filter(or_(User.username == login_value, User.email == login_value, User.phone == login_value, User.mxs_number == login_value)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    user.status = "online"
    user.last_seen_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/logout")
def logout(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.status = "offline"
    current_user.last_seen_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(payload: ProfileUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.display_name is not None:
        current_user.display_name = payload.display_name.strip()
    if payload.bio is not None:
        current_user.bio = payload.bio.strip()
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url.strip()
    if payload.status is not None:
        current_user.status = payload.status.strip() or "online"
    current_user.last_seen_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/search", response_model=list[UserOut])
def search_users(q: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = q.strip().lower()
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="Введите минимум 2 символа")
    normalized_phone = None
    try:
        normalized_phone = normalize_phone(q)
    except HTTPException:
        normalized_phone = None
    filters = [User.username.contains(q.lstrip("@")), User.display_name.contains(q), User.mxs_number.contains(q)]
    if "@" in q and not q.startswith("@"):
        filters.append(User.email.contains(q))
    if normalized_phone:
        filters.append(User.phone.contains(normalized_phone))
    return db.query(User).filter(User.id != current_user.id, or_(*filters)).limit(20).all()
