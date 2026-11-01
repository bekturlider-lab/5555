from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import select, delete
from ..models import User, Session, RecoveryRequest, Account
from ..models.identity import now
from ..config import settings
from ..core.security import digest, token, hash_password, verify_password, DUMMY_HASH
from ..core.rate_limits import consume
from ..core.audit import audit


def user_out(user):
    return {"id": user.id, "username": user.username, "full_name": user.full_name, "email": user.email, "role": user.role, "status": user.status, "created_at": user.created_at}


def make_session(db, user, request, response):
    from .consent import bind_request
    bind_request(db, request, user)
    raw, csrf = token(), token()
    ttl = settings().session_ttl_minutes * 60
    db.add(Session(id=digest(raw), user_id=user.id, csrf_hash=digest(csrf), user_agent=request.headers.get("user-agent", "Браузер")[:250], expires_at=now() + timedelta(seconds=ttl)))
    for name, value, http_only in [("campus_session", raw, True), ("campus_csrf", csrf, False)]:
        response.set_cookie(name, value, max_age=ttl, httponly=http_only, secure=settings().cookie_secure, samesite="lax", path="/")
    audit(db, user, "auth.login")
    return user_out(user)


def login(db, payload, request, response):
    ip = request.client.host if request.client else "unknown"
    consume(db, "login-ip:" + ip, 80)
    consume(db, "login:" + ip + ":" + payload.username.lower(), 10)
    user = db.scalar(select(User).where(User.username == payload.username.lower()))
    valid = verify_password(payload.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid or user.status != "active":
        db.commit()
        raise HTTPException(401, "Неверный логин или пароль либо доступ ограничен")
    return make_session(db, user, request, response)


def register(db, payload, request, response):
    from ..core.trusted_proxy import client_ip
    import secrets
    ip = client_ip(request, settings().trusted_proxy_cidrs) or "unknown"
    consume(db, "registration:" + ip, 5, 3600)
    if not payload.accept_training_terms:
        db.commit()
        raise HTTPException(400, "Подтвердите условия учебного проекта")
    username = payload.username.lower()
    if db.scalar(select(User.id).where(User.username == username)):
        db.commit()
        raise HTTPException(409, "Этот логин уже занят. Выберите другой.")
    user = User(username=username, full_name=payload.full_name, email=payload.email, password_hash=YOUR_VALUE_HERE, role="client", status="active", is_demo=False)
    db.add(user)
    db.flush()
    db.add(Account(user_id=user.id, reference="CB" + secrets.token_hex(5).upper(), name="Основной счёт", kind="current", balance=0))
    audit(db, user, "auth.registered")
    return make_session(db, user, request, response)


def request_recovery(db, payload, request):
    consume(db, "recovery:" + (request.client.host if request.client else "unknown"), 10, 3600)
    user = db.scalar(select(User).where(User.username == payload.username.lower()))
    if user:
        existing = db.scalar(select(RecoveryRequest).where(RecoveryRequest.user_id == user.id, RecoveryRequest.status == "pending"))
        if not existing:
            db.add(RecoveryRequest(user_id=user.id))
            audit(db, None, "auth.recovery_requested", user.id)
    return {"message": "Если учётная запись существует, запрос передан преподавателю. Получите у него одноразовый код."}


def reset_password(db, payload, request):
    consume(db, "reset:" + (request.client.host if request.client else "unknown"), 10)
    recovery = db.scalar(select(RecoveryRequest).where(RecoveryRequest.code_hash == digest(payload.code)).with_for_update())
    if not recovery or recovery.status != "issued" or not recovery.expires_at or recovery.expires_at <= now():
        db.commit()
        raise HTTPException(400, "Код недействителен или срок его действия истёк")
    user = db.get(User, recovery.user_id)
    user.password_hash = YOUR_VALUE_HERE
    recovery.status = "used"
    recovery.code_hash = None
    db.execute(delete(Session).where(Session.user_id == user.id))
    audit(db, user, "auth.password_reset")
    return {"message": "Пароль изменён. Войдите с новым паролем."}
