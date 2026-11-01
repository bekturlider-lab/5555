from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Input):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=1, max_length=128)


class Recovery(Input):
    username: str = Field(min_length=3, max_length=40)


class ResetPassword(Input):
    code: str = Field(min_length=20, max_length=100)
    password: str = Field(min_length=10, max_length=128)


class Register(Input):
    full_name: str = Field(min_length=3, max_length=120)
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: str = Field(min_length=5, max_length=160, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=10, max_length=128)
    accept_training_terms: bool
