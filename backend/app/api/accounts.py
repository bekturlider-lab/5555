from fastapi import APIRouter, Depends, Query
from ..db import get_db
from ..dependencies import current_user
from ..schemas.banking import OpenAccount
from ..services import accounts as service

router = APIRouter(tags=["Счета"])


@router.get("/accounts")
def listing(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return service.list_accounts(db, user)


@router.post("/accounts", status_code=201)
def create(payload: OpenAccount, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return service.open_account(db, user, payload)


@router.get("/recipients")
def recipient(reference: str = Query(min_length=3, max_length=40), db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return service.recipient(db, user, reference)
