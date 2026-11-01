import hmac
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from .db import get_db
from .models import User, Session
from .models.identity import now
from .core.security import digest


def current_user(request: Request, db=Depends(get_db, scope="function")):
    raw = request.cookies.get("campus_session", "")
    session = db.get(Session, digest(raw)) if raw else None
    user = db.get(User, session.user_id) if session else None
    if not session or session.expires_at <= now() or not user or user.status != "active":
        raise HTTPException(401, "Войдите в банк, чтобы продолжить")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        csrf = request.headers.get("X-CSRF-Token", "")
        if not csrf or not hmac.compare_digest(session.csrf_hash, digest(csrf)):
            raise HTTPException(403, "Не удалось проверить запрос. Обновите страницу.")
    request.state.session_id = session.id
    return user


def staff_user(user=Depends(current_user)):
    if user.role not in ("staff", "admin"):
        raise HTTPException(403, "Раздел доступен сотрудникам банка")
    return user


def admin_user(user=Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Требуется роль администратора")
    return user


def optional_user(request: Request, db=Depends(get_db, scope="function")):
    if not request.cookies.get("campus_session"):
        return None
    return current_user(request, db)
