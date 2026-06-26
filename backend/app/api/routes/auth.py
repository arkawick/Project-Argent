"""Staff authentication — single shared account, JWT issued on login."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from pydantic import BaseModel

from app.config import get_settings
from app.dependencies import get_current_user

router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends()) -> Token:
    cfg = get_settings()
    if form.username != cfg.staff_username or form.password != cfg.staff_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    expire = datetime.now(timezone.utc) + timedelta(minutes=cfg.access_token_expire_minutes)
    token = jwt.encode(
        {"sub": form.username, "exp": expire},
        cfg.secret_key,
        algorithm=cfg.algorithm,
    )
    return Token(access_token=token)


@router.get("/me")
async def me(user: dict = Depends(get_current_user)) -> dict:
    return {"username": user["username"], "role": "staff"}
