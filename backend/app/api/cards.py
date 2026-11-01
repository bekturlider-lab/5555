from fastapi import APIRouter, Depends
from ..db import get_db
from ..dependencies import current_user
from ..schemas.banking import IssueCard, CardStatus, CardLimit
from ..services import cards as service
from ..core.audit import audit

router = APIRouter(prefix="/cards", tags=["Карты"])


@router.get("")
def listing(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return service.list_cards(db, user)


@router.post("", status_code=201)
def create(payload: IssueCard, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return service.issue(db, user, payload)


@router.patch("/{card_id}/status")
def status(card_id: str, payload: CardStatus, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    card = service.owned_card(db, user, card_id, True)
    card.status = payload.status
    audit(db, user, "card.status", card.id, status=card.status)
    return service.card_out(db, card)


@router.patch("/{card_id}/limits")
def limits(card_id: str, payload: CardLimit, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    card = service.owned_card(db, user, card_id, True)
    card.daily_limit = payload.daily_limit
    audit(db, user, "card.limit", card.id, limit=card.daily_limit)
    return service.card_out(db, card)
