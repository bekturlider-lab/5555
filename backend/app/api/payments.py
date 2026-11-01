from fastapi import APIRouter, Depends
from sqlalchemy import select
from ..db import get_db
from ..dependencies import current_user
from ..models import Provider
from ..schemas.banking import PreviewPayment, ConfirmOperation
from ..services import transfers as service
from ..services.statements import transaction_out

router = APIRouter(prefix="/payments", tags=["Платежи"])


@router.get("/providers")
def providers(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return [{"id": p.id, "name": p.name, "category": p.category, "color": p.color, "icon": p.icon} for p in db.scalars(select(Provider).order_by(Provider.id))]


@router.post("/preview")
def preview(payload: PreviewPayment, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return service.preview(db, user, payload, True)


@router.post("")
def confirm(payload: ConfirmOperation, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return transaction_out(db, service.confirm(db, user, payload, True), user)
