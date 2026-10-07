"""Register, sign in, and sync shortlist / buyer prefs for an account."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from account_schemas import AuthResponse, BuyerPrefs, RegisterRequest, UserPublic
from auth import create_access_token, get_user_by_email, hash_password, verify_password
from users import MAX_SHORTLIST, User


def user_public(user: User) -> UserPublic:
    prefs = user.buyer_prefs()
    return UserPublic(
        id=user.id,
        email=user.email,
        name=user.name,
        shortlist=user.shortlist(),
        buyer_prefs=BuyerPrefs(**prefs) if prefs else None,
    )


def auth_payload(user: User) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user.id, user.email),
        user=user_public(user),
    )


def register_user(db: Session, body: RegisterRequest) -> AuthResponse:
    email = body.email.casefold().strip()
    name = " ".join(body.name.split())
    if not name:
        raise HTTPException(status_code=422, detail="Enter your name.")
    if get_user_by_email(db, email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )
    user = User(
        email=email,
        name=name,
        password_hash=hash_password(body.password),
        shortlist_json="[]",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return auth_payload(user)


def login_user(db: Session, email: str, password: str) -> AuthResponse:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is wrong.",
        )
    return auth_payload(user)


def merge_shortlist(server_ids: list[str], local_ids: list[str]) -> list[str]:
    merged: list[str] = []
    for item in [*server_ids, *local_ids]:
        value = str(item).strip()
        if value and value not in merged:
            merged.append(value)
        if len(merged) >= MAX_SHORTLIST:
            break
    return merged


def save_shortlist(db: Session, user: User, listing_ids: list[str]) -> UserPublic:
    user.set_shortlist(listing_ids)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_public(user)


def save_buyer_prefs(db: Session, user: User, prefs: dict | None) -> UserPublic:
    user.set_buyer_prefs(prefs)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_public(user)
