from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from ..db import get_db
from ..dependencies import current_user
from ..services import statements as service

router = APIRouter(prefix="/transactions", tags=["История"])


def filters(q: str = Query(default="", max_length=100), direction: str = Query(default="all", pattern="^(all|incoming|outgoing)$"), account_id: str = "", date_from: str = "", date_to: str = "", category: str = ""):
    return dict(q=q, direction=direction, account_id=account_id, date_from=date_from, date_to=date_to, category=category)


@router.get("")
def history(page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1, le=100), selected=Depends(filters), db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return service.history(db, user, page, page_size, **selected)


@router.get("/export")
def export(selected=Depends(filters), db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return Response(service.csv_export(db, user, **selected), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="b-bank-statement.csv"', "Cache-Control": "no-store"})


@router.get("/{tx_id}")
def detail(tx_id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return service.detail(db, user, tx_id)
