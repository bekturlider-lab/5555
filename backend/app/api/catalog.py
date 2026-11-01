import secrets
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select
from ..db import get_db
from ..dependencies import current_user, staff_user
from ..models import ProductOrder, User, Card
from ..models.identity import now
from ..schemas.auth import Input
from ..schemas.banking import OpenAccount, IssueCard
from ..services.accounts import open_account, list_accounts
from ..services.cards import issue
from ..content import PRODUCTS, PROMOTIONS, TEAM, public_product, product_by_id
from ..core.audit import audit, notify
from ..core.rate_limits import consume

router = APIRouter(tags=["Продукты и заявки"])


class OrderCreate(Input):
    product_id: str = Field(min_length=1, max_length=30)
    request_key: str = Field(min_length=16, max_length=80)
    note: str = Field(default="", max_length=1000)


class OrderUpdate(Input):
    status: Literal["in_review", "completed", "declined"]
    staff_note: str = Field(default="", max_length=1000)


@router.get("/public/content")
def content():
    return {"products": [public_product(p) for p in PRODUCTS], "promotions": PROMOTIONS, "team": TEAM, "fictional": True}


def order_out(db, order):
    user = db.get(User, order.user_id)
    product = product_by_id(order.product_id)
    return {"id": order.id, "reference": order.reference, "product_id": order.product_id, "product_name": product["name"] if product else order.product_id, "product_path": product["path"] if product else "/bank", "client_name": user.full_name, "username": user.username, "note": order.note, "status": order.status, "staff_note": order.staff_note, "created_at": order.created_at, "updated_at": order.updated_at, "fulfilled_id": order.fulfilled_id}


@router.post("/orders", status_code=201)
def create_order(payload: OrderCreate, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    previous = db.scalar(select(ProductOrder).where(ProductOrder.user_id == user.id, ProductOrder.request_key == payload.request_key))
    if previous:
        if previous.product_id != payload.product_id or previous.note != payload.note:
            raise HTTPException(409, "Ключ уже использован для другой заявки")
        return order_out(db, previous)
    if not product_by_id(payload.product_id):
        raise HTTPException(404, "Продукт не найден")
    consume(db, "orders:" + user.id, 20, 3600)
    order = ProductOrder(reference="AP-" + secrets.token_hex(5).upper(), user_id=user.id, product_id=payload.product_id, request_key=payload.request_key, note=payload.note)
    db.add(order)
    db.flush()
    audit(db, user, "order.created", order.id, product=order.product_id)
    notify(db, user.id, "Заявка принята", order.reference, "/bank/orders")
    return order_out(db, order)


@router.get("/orders")
def orders(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return [order_out(db, o) for o in db.scalars(select(ProductOrder).where(ProductOrder.user_id == user.id).order_by(ProductOrder.created_at.desc()).limit(200))]


@router.post("/orders/{order_id}/cancel")
def cancel(order_id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    order = db.scalar(select(ProductOrder).where(ProductOrder.id == order_id, ProductOrder.user_id == user.id).with_for_update())
    if not order:
        raise HTTPException(404, "Заявка не найдена")
    if order.status not in ("new", "in_review"):
        raise HTTPException(409, "Эту заявку уже нельзя отменить")
    order.status, order.updated_at = "cancelled", now()
    audit(db, user, "order.cancelled", order.id)
    return order_out(db, order)


@router.get("/staff/orders")
def staff_orders(db=Depends(get_db, scope="function"), user=Depends(staff_user)):
    return [order_out(db, o) for o in db.scalars(select(ProductOrder).order_by(ProductOrder.created_at.desc()).limit(200))]


@router.patch("/staff/orders/{order_id}")
def process_order(order_id: str, payload: OrderUpdate, db=Depends(get_db, scope="function"), user=Depends(staff_user)):
    order = db.scalar(select(ProductOrder).where(ProductOrder.id == order_id).with_for_update())
    if not order:
        raise HTTPException(404, "Заявка не найдена")
    if order.status in ("completed", "declined", "cancelled"):
        raise HTTPException(409, "Заявка уже завершена")
    client = db.scalar(select(User).where(User.id == order.user_id).with_for_update())
    if client.status != "active":
        raise HTTPException(400, "Доступ клиента ограничен")
    product = product_by_id(order.product_id)
    if not product:
        raise HTTPException(400, "Продукт больше не доступен")
    if payload.status == "completed":
        if product["fulfillment"] == "account":
            created = open_account(db, client, OpenAccount(name=product["name"], kind=product["kind"]))
            order.fulfilled_id = created["id"]
        elif product["fulfillment"] == "card":
            accounts = list_accounts(db, client)
            active = next((a for a in accounts if a["status"] == "active" and a["kind"] == "current"), None)
            if not active:
                raise HTTPException(400, "У клиента нет активного текущего счёта")
            created = issue(db, client, IssueCard(account_id=active["id"], color=product["color"]))
            order.fulfilled_id = created["id"]
            db.get(Card, created["id"]).label = product["name"]
    order.status, order.staff_note, order.updated_at = payload.status, payload.staff_note, now()
    audit(db, user, "order.status", order.id, status=payload.status)
    notify(db, client.id, "Статус заявки изменён", order.reference, "/bank/orders")
    return order_out(db, order)
