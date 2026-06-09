"""Optional JWT gate for BFF read APIs (enabled via BFF_REQUIRE_AUTH=1)."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import jwt
from fastapi import Header, HTTPException

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
REQUIRE_AUTH = os.getenv("BFF_REQUIRE_AUTH", "0") == "1"


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    if token.startswith("Bearer "):
        token = token[7:]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def require_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    if not REQUIRE_AUTH:
        return None
    payload = decode_token(authorization or "")
    if not payload:
        raise HTTPException(status_code=401, detail="invalid or missing token")
    return payload
