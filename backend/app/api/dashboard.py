from fastapi import APIRouter, Depends
from ..db import get_db
from ..dependencies import current_user
from ..services.dashboard import overview

router = APIRouter(tags=["Кабинет"])


@router.get("/dashboard")
def dashboard(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return overview(db, user)
