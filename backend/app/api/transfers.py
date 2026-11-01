from fastapi import APIRouter, Depends
from ..db import get_db
from ..dependencies import current_user
from ..schemas.banking import PreviewTransfer, ConfirmOperation
from ..services import transfers as service
from ..services.statements import transaction_out

router = APIRouter(prefix="/transfers", tags=["Переводы"])


@router.post("/preview")
def preview(payload: PreviewTransfer, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return service.preview(db, user, payload)


@router.post("")
def confirm(payload: ConfirmOperation, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return transaction_out(db, service.confirm(db, user, payload), user)
