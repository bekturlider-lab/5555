from fastapi import APIRouter, Depends, Request, Response, HTTPException
from sqlalchemy import select
from ..db import get_db
from ..dependencies import current_user
from ..models import User, Session
from ..schemas.auth import Login, Recovery, ResetPassword, Register
from ..services import auth as service
from ..config import settings
from ..core.rate_limits import consume

router = APIRouter(prefix="/auth", tags=["Вход"])


@router.post("/register", status_code=201)
def register(payload: Register, request: Request, response: Response, db=Depends(get_db, scope="function")):
    return service.register(db, payload, request, response)


@router.post("/login")
def login(payload: Login, request: Request, response: Response, db=Depends(get_db, scope="function")):
    return service.login(db, payload, request, response)


@router.get("/me")
def me(user=Depends(current_user)):
    return service.user_out(user)


@router.post("/logout")
def logout(request: Request, response: Response, user=Depends(current_user), db=Depends(get_db, scope="function")):
    db.delete(db.get(Session, request.state.session_id))
    response.delete_cookie("campus_session", path="/")
    response.delete_cookie("campus_csrf", path="/")
    return {"message": "Вы вышли из банка"}


@router.post("/recovery-requests")
def recovery(payload: Recovery, request: Request, db=Depends(get_db, scope="function")):
    return service.request_recovery(db, payload, request)


@router.post("/reset-password")
def reset(payload: ResetPassword, request: Request, db=Depends(get_db, scope="function")):
    return service.reset_password(db, payload, request)


@router.get("/options")
def options():
    return {"demo": settings().demo_quick_login, "bank_name": "B bank", "currency": "KGS"}


@router.post("/demo")
def demo(request: Request, response: Response, db=Depends(get_db, scope="function")):
    if not settings().demo_quick_login or settings().app_env == "production":
        raise HTTPException(404, "Страница не найдена")
    consume(db, "demo:" + (request.client.host if request.client else "unknown"), 30)
    user = db.scalar(select(User).where(User.username == "client001", User.is_demo.is_(True)))
    if not user:
        raise HTTPException(503, "Демонстрационные данные ещё не подготовлены")
    return service.make_session(db, user, request, response)
