from typing import Literal
from pydantic import Field
from .auth import Input


class UserStatus(Input):
    status: Literal["active", "blocked"]
    reason: str = Field(min_length=5, max_length=200)
