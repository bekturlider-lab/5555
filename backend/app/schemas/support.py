from typing import Literal
from pydantic import Field
from .auth import Input


class TicketCreate(Input):
    title: str = Field(min_length=3, max_length=120)
    category: Literal["Общий вопрос", "Переводы", "Карты", "Платежи", "Доступ"] = "Общий вопрос"
    message: str = Field(min_length=3, max_length=4000)


class MessageCreate(Input):
    message: str = Field(min_length=1, max_length=4000)


class TicketStatus(Input):
    status: Literal["open", "closed"]
