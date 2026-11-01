import hashlib
import hmac
import json
import time
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import select
from ..config import settings
from ..core.security import digest
from ..core.audit import audit
from ..legal_content import DOCUMENTS, FEATURES, LEGAL_DATE
from ..models import ConsentReceipt, ConsentAcceptance
from ..models.identity import now

COOKIE = "campus_terms"
MAX_AGE = 365 * 86400


def version():
    cfg = settings()
    body = json.dumps([DOCUMENTS, cfg.organizer_name, cfg.ai_provider_label], ensure_ascii=False, sort_keys=True)
    return "2026-10-27-" + hashlib.sha256(body.encode()).hexdigest()[:12]


def cookie_receipt(request):
    raw = request.cookies.get(COOKIE, "")
    try:
        receipt_id, stamp, revision, signature = raw.split("~")
        signed = "~".join([receipt_id, stamp, revision])
        if len(receipt_id) != 36 or revision != version() or not hmac.compare_digest(signature, digest("terms:" + signed)):
            return None
        age = time.time() - int(stamp)
        if age < -60 or age > MAX_AGE:
            return None
        return receipt_id
    except (ValueError, TypeError):
        return None


def receipt(db, request, lock=False):
    receipt_id = cookie_receipt(request)
    q = select(ConsentReceipt).where(ConsentReceipt.id == receipt_id, ConsentReceipt.version == version())
    row = db.scalar(q.with_for_update() if lock else q) if receipt_id else None
    if not row:
        raise HTTPException(428, "Сначала ознакомьтесь с соглашениями и подтвердите условия")
    return row


def public_bundle():
    return {"version": version(), "date": LEGAL_DATE, "organizer": settings().organizer_name, "documents": DOCUMENTS, "features": FEATURES, "ai_provider": settings().ai_provider_label}


def accept(db, payload, request, response, user=None):
    expected = {d['id'] for d in DOCUMENTS}
    if payload.version != version():
        raise HTTPException(409, "Документы изменились. Обновите страницу и ознакомьтесь с новой версией.")
    if not payload.agree or set(payload.reviewed_documents) != expected or len(payload.reviewed_documents) != len(expected):
        raise HTTPException(400, "Откройте все документы и подтвердите согласие с условиями")
    from ..core.rate_limits import consume
    from ..core.trusted_proxy import client_ip
    consume(db, "terms:" + (client_ip(request, settings().trusted_proxy_cidrs) or "unknown"), 30, 3600)
    row = ConsentReceipt(version=version(), documents=sorted(expected), ai_consent=False)
    db.add(row)
    db.flush()
    signed = "~".join([row.id, str(int(time.time())), row.version])
    response.set_cookie(COOKIE, signed + "~" + digest("terms:" + signed), max_age=MAX_AGE, httponly=True, secure=settings().cookie_secure, samesite="lax", path="/")
    if user:
        bind(db, row, user)
    else:
        audit(db, None, "legal.accepted", row.id, version=row.version)
    return {"accepted": True, "version": row.version, "accepted_at": row.accepted_at}


def bind(db, row, user):
    existing = db.scalar(select(ConsentAcceptance.id).where(ConsentAcceptance.receipt_id == row.id, ConsentAcceptance.user_id == user.id))
    if not existing:
        db.add(ConsentAcceptance(receipt_id=row.id, user_id=user.id))
        audit(db, user, "legal.accepted", row.id, version=row.version)


def bind_request(db, request, user):
    bind(db, receipt(db, request), user)
