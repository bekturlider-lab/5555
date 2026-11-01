from typing import Literal
from pydantic import Field
from .auth import Input


class OpenAccount(Input):
    name: str = Field(min_length=2, max_length=60)
    kind: Literal["current", "savings"] = "current"


class IssueCard(Input):
    account_id: str = Field(max_length=36)
    color: Literal["graphite", "yellow", "silver"] = "graphite"


class CardStatus(Input):
    status: Literal["active", "frozen"]


class CardLimit(Input):
    daily_limit: int = Field(strict=True, ge=100, le=100000000)


class PreviewTransfer(Input):
    from_account_id: str = Field(max_length=36)
    to_reference: str = Field(min_length=3, max_length=40)
    amount: int = Field(strict=True, ge=100, le=100000000)
    description: str = Field(default="", max_length=180)
    card_id: str | None = Field(default=None, max_length=36)


class PreviewPayment(Input):
    from_account_id: str = Field(max_length=36)
    provider_id: str = Field(max_length=30)
    customer_reference: str = Field(min_length=3, max_length=60, pattern=r"^[а-яА-ЯёЁa-zA-Z0-9 +()._-]+$")
    amount: int = Field(strict=True, ge=100, le=100000000)
    card_id: str | None = Field(default=None, max_length=36)


class ConfirmOperation(Input):
    intent_id: str = Field(max_length=36)
    idempotency_key: str = Field(min_length=16, max_length=100)
