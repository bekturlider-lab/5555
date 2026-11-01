from fastapi import HTTPException
from sqlalchemy import select, or_
from ..models import Ticket, Message, User
from ..models.identity import now
from ..core.audit import audit, notify


def visible(db, user, ticket_id):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(404, "Обращение не найдено")
    if user.role == "client" and ticket.user_id != user.id:
        raise HTTPException(404, "Обращение не найдено")
    if user.role == "staff" and ticket.assigned_to not in (None, user.id):
        raise HTTPException(403, "Обращение назначено другому сотруднику")
    return ticket


def ticket_out(db, ticket, messages=False):
    owner = db.get(User, ticket.user_id)
    result = {"id": ticket.id, "title": ticket.title, "category": ticket.category, "status": ticket.status, "client_name": owner.full_name, "created_at": ticket.created_at, "updated_at": ticket.updated_at}
    if messages:
        result['messages'] = [{"id": m.id, "body": m.body, "author": db.get(User, m.author_id).full_name, "role": db.get(User, m.author_id).role, "created_at": m.created_at} for m in db.scalars(select(Message).where(Message.ticket_id == ticket.id).order_by(Message.created_at))]
    return result


def listing(db, user, staff=False):
    q = select(Ticket)
    if not staff:
        q = q.where(Ticket.user_id == user.id)
    elif user.role == "staff":
        q = q.where(or_(Ticket.assigned_to.is_(None), Ticket.assigned_to == user.id))
    return [ticket_out(db, t) for t in db.scalars(q.order_by(Ticket.updated_at.desc()).limit(200))]


def create(db, user, payload):
    ticket = Ticket(user_id=user.id, title=payload.title, category=payload.category)
    db.add(ticket)
    db.flush()
    db.add(Message(ticket_id=ticket.id, author_id=user.id, body=payload.message))
    audit(db, user, "support.created", ticket.id)
    db.flush()
    return ticket_out(db, ticket, True)


def reply(db, user, ticket_id, message):
    ticket = visible(db, user, ticket_id)
    # Serialise replies and closing to keep the conversation state consistent.
    ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
    if user.role == "staff" and ticket.assigned_to not in (None, user.id):
        raise HTTPException(403, "Обращение назначено другому сотруднику")
    if ticket.status == "closed":
        raise HTTPException(400, "Обращение закрыто. Создайте новое.")
    if user.role in ("staff", "admin"):
        ticket.assigned_to = user.id
        ticket.status = "answered"
        notify(db, ticket.user_id, "Поддержка ответила", ticket.title, "/bank/support/" + ticket.id)
    else:
        ticket.status = "open"
    ticket.updated_at = now()
    db.add(Message(ticket_id=ticket.id, author_id=user.id, body=message))
    audit(db, user, "support.replied", ticket.id)
    db.flush()
    return ticket_out(db, ticket, True)
