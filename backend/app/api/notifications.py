from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from ..db import get_db
from ..dependencies import current_user
from ..models import Notification

router = APIRouter(prefix="/notifications", tags=["Уведомления"])


@router.get("")
def listing(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return [{"id": n.id, "title": n.title, "body": n.body, "link": n.link, "is_read": n.is_read, "created_at": n.created_at} for n in db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(200))]


@router.post("/read-all")
def all_read(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    db.execute(update(Notification).where(Notification.user_id == user.id).values(is_read=True))
    return {"message": "Уведомления прочитаны"}


@router.patch("/{notification_id}")
def read(notification_id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "Уведомление не найдено")
    n.is_read = True
    return {"message": "Прочитано"}
