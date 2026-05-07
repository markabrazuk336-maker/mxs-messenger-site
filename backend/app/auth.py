import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from email_validator import validate_email as check_email, EmailNotValidError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_\.]{3,32}$")


def normalize_username(username: str) -> str:
    return username.strip().lower().lstrip("@")


def validate_username(username: str) -> str:
    username = normalize_username(username)
    if not USERNAME_RE.match(username):
        raise HTTPException(
            status_code=400,
            detail="Username должен быть 3–32 символа: латиница, цифры, точка или _",
        )
    if ".." in username or username.startswith(".") or username.endswith("."):
        raise HTTPException(
            status_code=400,
            detail="Username не должен начинаться/заканчиваться точкой или содержать две точки подряд",
        )
    return username


def normalize_email(email: str) -> str:
    raw = email.strip().lower()
    try:
        result = check_email(raw, check_deliverability=False)
        return result.normalized.lower()
    except EmailNotValidError:
        raise HTTPException(status_code=400, detail="Введите корректный email, например name@gmail.com")


def normalize_phone(phone: str | None, required: bool = False) -> str | None:
    if phone is None or phone.strip() == "":
        if required:
            raise HTTPException(status_code=400, detail="Введите номер телефона")
        return None

    raw = phone.strip()
    if re.search(r"[a-zA-Zа-яА-Я]", raw):
        raise HTTPException(status_code=400, detail="Телефон не должен содержать буквы")

    digits = re.sub(r"\D", "", raw)

    if len(digits) == 10:
        # Российский номер без кода страны: 9991234567 -> +79991234567
        digits = "7" + digits
    elif len(digits) == 11 and digits.startswith("8"):
        # 89991234567 -> +79991234567
        digits = "7" + digits[1:]

    if len(digits) < 10 or len(digits) > 15:
        raise HTTPException(status_code=400, detail="Телефон должен содержать от 10 до 15 цифр")

    return "+" + digits


def normalize_login(value: str) -> str:
    value = value.strip().lower()
    if "@" in value and not value.startswith("@"):  # email
        return normalize_email(value)
    if any(ch.isdigit() for ch in value) and not USERNAME_RE.match(value.lstrip("@")):
        phone = normalize_phone(value)
        return phone or value
    return normalize_username(value)


def validate_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Пароль должен быть минимум 8 символов")
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Пароль слишком длинный. Максимум 72 байта")


def hash_password(password: str) -> str:
    validate_password(password)
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить токен",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise credentials_exception
    return user


def generate_mxs_number(db: Session) -> str:
    for _ in range(50):
        num = str(secrets.randbelow(90000000) + 10000000)
        exists = db.query(User).filter(User.mxs_number == num).first()
        if not exists:
            return num
    raise HTTPException(status_code=500, detail="Не удалось создать MXS-номер")
