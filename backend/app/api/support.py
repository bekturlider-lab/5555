from fastapi import APIRouter, Depends
from ..db import get_db
from ..dependencies import current_user
from ..schemas.support import TicketCreate, MessageCreate, TicketStatus
from ..services import support as service
from ..models import Ticket
from ..models.identity import now
from sqlalchemy import select
from ..core.audit import audit

router = APIRouter(prefix="/support/tickets", tags=["Поддержка"])


@router.get("")
def listing(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return service.listing(db, user)


@router.post("", status_code=201)
def create(payload: TicketCreate, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return service.create(db, user, payload)


@router.get("/{ticket_id}")
def detail(ticket_id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return service.ticket_out(db, service.visible(db, user, ticket_id), True)


@router.post("/{ticket_id}/messages")
def reply(ticket_id: str, payload: MessageCreate, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return service.reply(db, user, ticket_id, payload.message)


@router.patch("/{ticket_id}/status")
def status(ticket_id: str, payload: TicketStatus, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    service.visible(db, user, ticket_id)
    ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
    ticket.status = payload.status
    ticket.updated_at = now()
    audit(db, user, "support.status", ticket.id, status=ticket.status)
    return service.ticket_out(db, ticket, True)
