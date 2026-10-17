from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import LoginRequest, MessageResponse, RegisterRequest, TokenResponse, UserOut
from ..security import (
    create_access_token,
    get_token_payload,
    hash_password,
    login_throttle,
    revoke_token,
    user_exists,
    verify_password_or_dummy,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _token_response(user: User) -> TokenResponse:
    token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in, user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = body.email.lower()
    if user_exists(db, email):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    user = User(email=email, full_name=body.full_name, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:  # concurrent registration with the same e-mail
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.") from exc
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = body.email.lower()
    if login_throttle.is_blocked(email):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Too many failed sign-in attempts. Please wait 15 minutes and try again.")
    user = db.scalar(select(User).where(User.email == email))
    if not verify_password_or_dummy(body.password, user):
        login_throttle.record_failure(email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    login_throttle.reset(email)
    return _token_response(user)


@router.post("/logout", response_model=MessageResponse)
def logout(payload: dict = Depends(get_token_payload), db: Session = Depends(get_db)) -> MessageResponse:
    revoke_token(db, payload)
    return MessageResponse(detail="Signed out.")
