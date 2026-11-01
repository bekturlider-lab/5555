from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import select, delete
from ..db import get_db
from ..dependencies import current_user
from ..models import Session
from ..models.identity import now
from ..schemas.profile import ProfileUpdate, PasswordUpdate
from ..services.auth import user_out
from ..core.security import hash_password, verify_password
from ..core.rate_limits import consume
from ..core.audit import audit

router = APIRouter(prefix="/profile", tags=["Профиль"])


@router.get("")
def get_profile(user=Depends(current_user)):
    return user_out(user)


@router.patch("")
def update(payload: ProfileUpdate, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    user.full_name, user.email = payload.full_name, payload.email
    audit(db, user, "profile.updated")
    return user_out(user)


@router.post("/password")
def password(payload: PasswordUpdate, request: Request, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    consume(db, "password:" + user.id, 8)
    if not verify_password(payload.current_password, user.password_hash):
        db.commit()
        raise HTTPException(400, "Текущий пароль указан неверно")
    user.password_hash = YOUR_VALUE_HERE
    db.execute(delete(Session).where(Session.user_id == user.id, Session.id != request.state.session_id))
    audit(db, user, "profile.password_changed")
    return {"message": "Пароль изменён. Остальные сеансы завершены."}


@router.get("/sessions")
def sessions(request: Request, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return [{"id": s.id, "user_agent": s.user_agent, "created_at": s.created_at, "expires_at": s.expires_at, "current": s.id == request.state.session_id} for s in db.scalars(select(Session).where(Session.user_id == user.id, Session.expires_at > now()).order_by(Session.created_at.desc()))]


@router.post("/sessions/revoke-others")
def revoke_others(request: Request, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    db.execute(delete(Session).where(Session.user_id == user.id, Session.id != request.state.session_id))
    audit(db, user, "sessions.revoked_others")
    return {"message": "Остальные сеансы завершены"}


@router.delete("/sessions/{session_id}")
def revoke(session_id: str, request: Request, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    session = db.get(Session, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(404, "Сеанс не найден")
    if session.id == request.state.session_id:
        raise HTTPException(400, "Для текущего сеанса используйте кнопку выхода")
    db.delete(session)
    audit(db, user, "session.revoked", session_id)
    return {"message": "Сеанс завершён"}
