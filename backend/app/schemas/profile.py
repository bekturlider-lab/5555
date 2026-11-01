from pydantic import Field
from .auth import Input


class ProfileUpdate(Input):
    full_name: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=5, max_length=160, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class PasswordUpdate(Input):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)
