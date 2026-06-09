"""Password hashing — bcrypt primary, Werkzeug legacy fallback."""

from __future__ import annotations

import bcrypt
from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(stored_hash: str, password: str) -> bool:
    if not stored_hash or not password:
        return False
    if stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
        except Exception:
            return False
    if stored_hash.startswith(("pbkdf2:", "scrypt:", "$argon2")):
        try:
            return check_password_hash(stored_hash, password)
        except Exception:
            return False
    return False


def needs_rehash(stored_hash: str) -> bool:
    return not stored_hash.startswith(("$2a$", "$2b$", "$2y$"))


def upgrade_hash(password: str) -> str:
    return hash_password(password)
