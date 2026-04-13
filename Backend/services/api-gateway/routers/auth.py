import re
from datetime import datetime, timezone

from config import get_settings
from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    message: str
    email: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    message: str
    email: str


def _get_users_collection():
    settings = get_settings()
    client = MongoClient(settings.MONGO_URI)
    db = client["rag_db"]
    collection = db["users"]
    collection.create_index("email", unique=True)
    return collection


def _validate_password(password: str) -> str | None:
    """Return an error message if the password is too weak, else None."""
    if len(password) < 8:
        return "รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร"
    if not re.search(r"[A-Za-z]", password):
        return "รหัสผ่านต้องมีตัวอักษรอย่างน้อย 1 ตัว"
    if not re.search(r"\d", password):
        return "รหัสผ่านต้องมีตัวเลขอย่างน้อย 1 ตัว"
    return None


@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
    err = _validate_password(request.password)
    if err:
        raise HTTPException(status_code=400, detail=err)

    hashed = pwd_context.hash(request.password)
    collection = _get_users_collection()

    try:
        collection.insert_one(
            {
                "email": request.email,
                "hashed_password": hashed,
                "created_at": datetime.now(timezone.utc),
            }
        )
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="อีเมลนี้ถูกใช้งานแล้ว")

    return RegisterResponse(message="ลงทะเบียนสำเร็จ", email=request.email)


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    collection = _get_users_collection()
    user = collection.find_one({"email": request.email})

    if not user or not pwd_context.verify(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="อีเมลหรือรหัสผ่านไม่ถูกต้อง")

    return LoginResponse(message="เข้าสู่ระบบสำเร็จ", email=user["email"])
