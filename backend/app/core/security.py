import hashlib
import hmac
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from ..config import settings

hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
DUMMY_HASH = hasher.hash("dummy-password-never-used-for-login")


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def digest(value: str) -> str:
    return hmac.new(settings().app_secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def token():
    return secrets.token_urlsafe(32)
