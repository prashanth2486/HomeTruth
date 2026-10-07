"""Account routes: register, login, session, synced shortlist and buyer prefs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from account_schemas import (
    AuthResponse,
    BuyerPrefs,
    LoginRequest,
    RegisterRequest,
    ShortlistUpdate,
    UserPublic,
)
from accounts import (
    login_user,
    register_user,
    save_buyer_prefs,
    save_shortlist,
    user_public,
)
from auth import current_user
from db import get_db
from users import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterRequest, db: Annotated[Session, Depends(get_db)]):
    return register_user(db, body)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    return login_user(db, body.email, body.password)


@router.get("/me", response_model=UserPublic)
def me(user: Annotated[User, Depends(current_user)]):
    return user_public(user)


@router.put("/me/shortlist", response_model=UserPublic)
def update_shortlist(
    body: ShortlistUpdate,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return save_shortlist(db, user, body.listing_ids)


@router.put("/me/buyer", response_model=UserPublic)
def update_buyer(
    body: BuyerPrefs,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return save_buyer_prefs(db, user, body.model_dump(exclude_none=True))


@router.delete("/me/buyer", response_model=UserPublic)
def clear_buyer(
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return save_buyer_prefs(db, user, None)
