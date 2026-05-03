from auth.dependencies import CurrentUser, require_admin, require_user
from auth.jwt_utils import encode_token
from auth.passwords import hash_password, verify_password
from config import Settings, get_settings
from fastapi import APIRouter, Depends, HTTPException
from logger import log
from pydantic import BaseModel, Field
from state import gRPCState

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    user_id: str
    username: str
    role: str
    staff_id: int | None = None


class LoginResponse(BaseModel):
    token: str
    user: UserPublic


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=6)
    role: str = Field(pattern="^(admin|user)$")
    staff_id: int | None = None


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, settings: Settings = Depends(get_settings)):
    store = gRPCState.user_store
    doc = store.find_by_username(req.username)
    if not doc or not verify_password(req.password, doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user_id = doc["user_id"]
    role = doc.get("role", "user")
    staff_id = doc.get("staff_id")

    token = encode_token(
        user_id=user_id,
        username=doc["username"],
        role=role,
        staff_id=staff_id,
        secret=settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
        expires_hours=settings.JWT_EXPIRES_HOURS,
    )

    return LoginResponse(
        token=token,
        user=UserPublic(
            user_id=user_id,
            username=doc["username"],
            role=role,
            staff_id=staff_id,
        ),
    )


@router.get("/me", response_model=UserPublic)
async def me(user: CurrentUser = Depends(require_user)):
    return UserPublic(
        user_id=user.user_id,
        username=user.username,
        role=user.role,
        staff_id=user.staff_id,
    )


@router.post("/users", response_model=UserPublic, status_code=201)
async def create_user(
    req: CreateUserRequest,
    _admin: CurrentUser = Depends(require_admin),
):
    store = gRPCState.user_store

    if store.find_by_username(req.username):
        raise HTTPException(status_code=409, detail="Username already exists")

    if req.role == "user" and req.staff_id is None:
        raise HTTPException(
            status_code=400,
            detail="staff_id is required for users (used to filter ticket access).",
        )

    user_id = store.create_user(
        username=req.username,
        password_hash=hash_password(req.password),
        role=req.role,
        staff_id=req.staff_id,
    )
    log.info(f"Admin created new account: {req.username} (role={req.role}, staff_id={req.staff_id})")

    return UserPublic(
        user_id=user_id,
        username=req.username,
        role=req.role,
        staff_id=req.staff_id,
    )
