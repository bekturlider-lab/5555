from fastapi import APIRouter, Depends, Request, Response
from pydantic import Field
from sqlalchemy import delete
from ..schemas.auth import Input
from ..db import get_db
from ..dependencies import optional_user
from ..models import AiConversation
from ..models.identity import now
from ..services import consent
from ..core.audit import audit

router = APIRouter(prefix="/legal", tags=["Соглашения"])


class Accept(Input):
    version: str = Field(max_length=40)
    reviewed_documents: list[str] = Field(max_length=4)
    agree: bool


class AiConsent(Input):
    enabled: bool


@router.get("/status")
def status(request: Request, db=Depends(get_db, scope="function")):
    row = db.get(consent.ConsentReceipt, consent.cookie_receipt(request)) if consent.cookie_receipt(request) else None
    return {**consent.public_bundle(), "accepted": bool(row), "ai_consent": bool(row and row.ai_consent), "accepted_at": row.accepted_at if row else None}


@router.post("/accept")
def accept(payload: Accept, request: Request, response: Response, db=Depends(get_db, scope="function"), user=Depends(optional_user)):
    return consent.accept(db, payload, request, response, user)


@router.post("/ai-consent")
def ai_consent(payload: AiConsent, request: Request, db=Depends(get_db, scope="function"), user=Depends(optional_user)):
    row = consent.receipt(db, request, lock=True)
    row.ai_consent, row.ai_changed_at = payload.enabled, now()
    if not payload.enabled:
        db.execute(delete(AiConversation).where(AiConversation.receipt_id == row.id))
    audit(db, user, "legal.ai_consent", row.id, enabled=payload.enabled, version=row.version)
    return {"ai_consent": row.ai_consent}
