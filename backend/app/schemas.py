from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=24)
    display_name: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=8, max_length=72)

class UserLogin(BaseModel):
    login: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=72)

class UserOut(BaseModel):
    id: int
    mxs_number: str
    username: str
    email: EmailStr
    phone: str
    display_name: str
    bio: str = ""
    avatar_url: str = ""
    status: str = "offline"
    last_seen_at: datetime | None = None
    created_at: datetime
    model_config = {"from_attributes": True}

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=64)
    bio: str | None = Field(default=None, max_length=300)
    avatar_url: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, max_length=32)

class ChatCreate(BaseModel):
    target: str = Field(min_length=3, max_length=120)

class GroupCreate(BaseModel):
    title: str = Field(min_length=2, max_length=80)
    members: list[str] = Field(default_factory=list)

class ChatOut(BaseModel):
    id: int
    type: str
    title: str
    avatar_url: str = ""
    other_user: UserOut | None = None
    members_count: int = 0
    last_message: str | None = None
    last_message_type: str | None = None
    last_message_at: datetime | None = None
    unread_count: int = 0

class MessageCreate(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

class MessageEdit(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

class MessageOut(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    text: str = ""
    message_type: str = "text"
    file_url: str = ""
    file_name: str = ""
    file_mime: str = ""
    file_size: int = 0
    is_deleted: bool = False
    edited_at: datetime | None = None
    created_at: datetime
    model_config = {"from_attributes": True}
