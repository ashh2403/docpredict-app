from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import AccountDelete, MessageResponse, PasswordChange, ProfileUpdate, UserOut
from ..security import get_current_user, get_token_payload, hash_password, revoke_token, verify_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def read_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.theme is not None:
        user.theme = body.theme
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/password", response_model=MessageResponse)
def change_password(body: PasswordChange, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)) -> MessageResponse:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect.")
    if body.current_password == body.new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "New password must be different from the current one.")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return MessageResponse(detail="Password updated.")


@router.delete("/me", response_model=MessageResponse)
def delete_me(body: AccountDelete, user: User = Depends(get_current_user),
              payload: dict = Depends(get_token_payload), db: Session = Depends(get_db)) -> MessageResponse:
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password is incorrect.")
    db.delete(user)  # cascades to all of the user's analyses
    db.commit()
    revoke_token(db, payload)
    return MessageResponse(detail="Account and all saved analyses deleted.")
