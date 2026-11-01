from fastapi import APIRouter, Depends, Request
from pydantic import Field
from ..db import get_db
from ..dependencies import optional_user
from ..schemas.auth import Input
from ..services import ai_support

router = APIRouter(prefix="/ai", tags=["AI-поддержка"])


class Chat(Input):
    message: str = Field(min_length=1, max_length=2000)
    request_key: str = Field(min_length=16, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")


@router.get("/state")
def state(request: Request, db=Depends(get_db, scope="function"), user=Depends(optional_user)):
    return ai_support.state(db, request, user)


@router.post("/chat")
def chat(payload: Chat, request: Request, db=Depends(get_db, scope="function"), user=Depends(optional_user)):
    return ai_support.chat(db, request, user, payload)


@router.post("/handoff")
def handoff(payload: Chat, request: Request, db=Depends(get_db, scope="function"), user=Depends(optional_user)):
    return ai_support.chat(db, request, user, payload, human=True)


@router.delete("/state")
def clear(request: Request, db=Depends(get_db, scope="function"), user=Depends(optional_user)):
    return ai_support.clear(db, request, user)
