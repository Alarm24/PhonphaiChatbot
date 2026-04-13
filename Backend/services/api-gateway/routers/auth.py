import re

import psycopg
from config import get_settings
from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

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


def _get_conninfo() -> str:
    s = get_settings()
    return (
        f"host={s.POSTGRES_HOST} port={s.POSTGRES_PORT} "
        f"dbname={s.POSTGRES_DB} user={s.POSTGRES_USER} password={s.POSTGRES_PASSWORD}"
    )


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

    try:
        with psycopg.connect(_get_conninfo()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (email, hashed_password) VALUES (%s, %s)",
                    (request.email, hashed),
                )
            conn.commit()
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="อีเมลนี้ถูกใช้งานแล้ว")

    return RegisterResponse(message="ลงทะเบียนสำเร็จ", email=request.email)


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    with psycopg.connect(_get_conninfo(), row_factory=psycopg.rows.dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (request.email,))
            user = cur.fetchone()

    if not user or not pwd_context.verify(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="อีเมลหรือรหัสผ่านไม่ถูกต้อง")

    return LoginResponse(message="เข้าสู่ระบบสำเร็จ", email=user["email"])
