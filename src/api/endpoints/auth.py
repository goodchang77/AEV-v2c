"""
認證 API 端點
Authentication API Endpoints

提供註冊、登入（JWT）、當前使用者查詢。使用 python-jose + passlib[bcrypt]。
"""

from datetime import datetime, timedelta
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.database import SessionLocal
from src.models import User

router = APIRouter()

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ---------------------------------------------------------------------------
# 依賴：同步 DB session（正確關閉）
# ---------------------------------------------------------------------------
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 請求/回應模型
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=100)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ---------------------------------------------------------------------------
# 密碼與 JWT 輔助
# ---------------------------------------------------------------------------
def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """驗證 JWT 並回傳目前使用者"""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無效的認證憑證",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    try:
        user = db.query(User).filter(User.user_id == uuid.UUID(user_id)).first()
    except (ValueError, AttributeError):
        user = None
    if user is None:
        raise credentials_exc
    return user


# ---------------------------------------------------------------------------
# 端點
# ---------------------------------------------------------------------------
@router.get("/")
async def auth_status():
    """認證狀態檢查"""
    return {"status": "auth_service_available", "message": "認證服務運行中"}


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """註冊新使用者並回傳 JWT"""
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="使用者名稱已被使用")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email 已被使用")

    user = User(
        username=req.username,
        email=req.email,
        password_hash=_hash_password(req.password),
        full_name=req.full_name,
        role="user",
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.user_id), user.username)
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """登入並回傳 JWT"""
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not _verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="使用者名稱或密碼錯誤")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="帳戶已停用")

    token = create_access_token(str(user.user_id), user.username)
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    """查詢目前使用者資訊（需 JWT）"""
    return {
        "user_id": str(current_user.user_id),
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "full_name": current_user.full_name,
    }
