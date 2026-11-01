from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import select, text
from ..models import RateBucket
from ..models.identity import now
from .security import digest


def consume(db, key: str, limit: int, seconds: int = 900):
    key_hash = digest(key)
    lock_key = int(key_hash[:15], 16)
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
    bucket = db.get(RateBucket, key_hash)
    stamp = now()
    if bucket is None:
        bucket = RateBucket(id=key_hash, started_at=stamp, count=0)
        db.add(bucket)
    if bucket.started_at + timedelta(seconds=seconds) <= stamp:
        bucket.started_at = stamp
        bucket.count = 0
    bucket.count += 1
    db.flush()
    if bucket.count > limit:
        db.commit()
        raise HTTPException(429, "Слишком много попыток. Попробуйте позже.", headers={"Retry-After": str(seconds)})
