from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, delete, or_
from ..db import get_db
from ..dependencies import staff_user, admin_user
from ..models import User, Session, Ticket, BankTransaction, RecoveryRequest, AuditEvent
from ..models.identity import now
from ..schemas.staff import UserStatus
from ..schemas.support import MessageCreate, TicketStatus
from ..services import support, auth, accounts
from ..core.audit import audit
from ..core.money import day_start
from ..core.security import token, digest

router = APIRouter(prefix="/staff", tags=["Сотрудники"])


@router.get("/overview")
def overview(db=Depends(get_db, scope="function"), user=Depends(staff_user)):
    start = day_start()
    clients = db.execute(select(
        func.count(User.id).label("clients"),
        func.count(User.id).filter(User.is_demo.is_(False)).label("registered_clients"),
        func.count(User.id).filter(User.is_demo.is_(True)).label("demo_clients"),
        func.count(User.id).filter(User.is_demo.is_(False), User.created_at >= start).label("registered_today"),
        func.count(User.id).filter(User.status == "blocked").label("blocked"),
    ).where(User.role == "client")).mappings().one()
    return {**clients, "open_tickets": db.scalar(select(func.count()).select_from(Ticket).where(Ticket.status != "closed")), "today_operations": db.scalar(select(func.count()).select_from(BankTransaction).where(BankTransaction.created_at >= start, BankTransaction.kind != "opening"))}


@router.get("/users")
def users(q: str = Query(default="", max_length=100), db=Depends(get_db, scope="function"), user=Depends(admin_user)):
    query = select(User).where(User.role == "client")
    if q:
        query = query.where(or_(User.full_name.ilike("%" + q + "%"), User.username.ilike("%" + q + "%")))
    return [auth.user_out(u) for u in db.scalars(query.order_by(User.username).limit(200))]


@router.get("/users/{user_id}")
def detail(user_id: str, db=Depends(get_db, scope="function"), user=Depends(admin_user)):
    target = db.get(User, user_id)
    if not target or target.role != "client":
        raise HTTPException(404, "Клиент не найден")
    return {**auth.user_out(target), "accounts": accounts.list_accounts(db, target)}


@router.patch("/users/{user_id}/status")
def status(user_id: str, payload: UserStatus, db=Depends(get_db, scope="function"), user=Depends(admin_user)):
    target = db.scalar(select(User).where(User.id == user_id, User.role == "client").with_for_update())
    if not target:
        raise HTTPException(404, "Клиент не найден")
    target.status = payload.status
    if payload.status == "blocked":
        db.execute(delete(Session).where(Session.user_id == target.id))
    audit(db, user, "client.status", target.id, status=payload.status, reason=payload.reason)
    return auth.user_out(target)


@router.get("/tickets")
def tickets(db=Depends(get_db, scope="function"), user=Depends(staff_user)):
    return support.listing(db, user, True)


@router.get("/tickets/{ticket_id}")
def ticket_detail(ticket_id: str, db=Depends(get_db, scope="function"), user=Depends(staff_user)):
    return support.ticket_out(db, support.visible(db, user, ticket_id), True)


@router.post("/tickets/{ticket_id}/messages")
def reply(ticket_id: str, payload: MessageCreate, db=Depends(get_db, scope="function"), user=Depends(staff_user)):
    return support.reply(db, user, ticket_id, payload.message)


@router.patch("/tickets/{ticket_id}/status")
def ticket_status(ticket_id: str, payload: TicketStatus, db=Depends(get_db, scope="function"), user=Depends(staff_user)):
    ticket = support.visible(db, user, ticket_id)
    ticket.status = payload.status
    ticket.updated_at = now()
    audit(db, user, "support.status", ticket.id, status=payload.status)
    return support.ticket_out(db, ticket, True)


@router.get("/recovery-requests")
def recoveries(db=Depends(get_db, scope="function"), user=Depends(admin_user)):
    return [{"id": r.id, "username": db.get(User, r.user_id).username, "full_name": db.get(User, r.user_id).full_name, "status": r.status, "created_at": r.created_at, "expires_at": r.expires_at} for r in db.scalars(select(RecoveryRequest).order_by(RecoveryRequest.created_at.desc()).limit(200))]


@router.post("/recovery-requests/{recovery_id}/issue-code")
def issue(recovery_id: str, db=Depends(get_db, scope="function"), user=Depends(admin_user)):
    recovery = db.scalar(select(RecoveryRequest).where(RecoveryRequest.id == recovery_id).with_for_update())
    if not recovery or recovery.status == "used":
        raise HTTPException(404, "Запрос не найден")
    if recovery.status == "issued" and recovery.expires_at and recovery.expires_at > now():
        raise HTTPException(409, "Код уже выдан и ещё действует")
    raw = token()
    recovery.code_hash = digest(raw)
    recovery.status = "issued"
    recovery.expires_at = now() + timedelta(minutes=15)
    audit(db, user, "auth.recovery_code_issued", recovery.id)
    return {"code": raw, "expires_at": recovery.expires_at}


@router.get("/audit")
def audit_events(page: int = Query(default=1, ge=1), q: str = Query(default="", max_length=100), db=Depends(get_db, scope="function"), user=Depends(admin_user)):
    query = select(AuditEvent)
    if q:
        query = query.where(AuditEvent.action.ilike("%" + q + "%"))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    events = db.scalars(query.order_by(AuditEvent.created_at.desc()).offset((page - 1) * 25).limit(25))
    return {"items": [{"id": e.id, "action": e.action, "actor": db.get(User, e.actor_id).full_name if e.actor_id and db.get(User, e.actor_id) else "Система", "entity_id": e.entity_id, "details": e.details, "created_at": e.created_at} for e in events], "total": total, "page": page, "page_size": 25}
