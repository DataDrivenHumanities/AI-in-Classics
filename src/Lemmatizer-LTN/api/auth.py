"""
Bearer token authentication for the Latin Lemmatizer API.

Tokens are read from the API_TOKENS environment variable (comma-separated).
Each researcher or service can have their own token for easy revocation.
"""

import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer_scheme = HTTPBearer()

# Cache parsed tokens at module level; refreshed on first call or when empty.
_valid_tokens: Optional[set[str]] = None


def _load_tokens() -> set[str]:
    """Load valid tokens from the API_TOKENS env var."""
    raw = os.getenv("API_TOKENS", "")
    tokens = {t.strip() for t in raw.split(",") if t.strip()}
    if not tokens:
        raise RuntimeError(
            "No API tokens configured. Set the API_TOKENS environment variable "
            "(comma-separated list of bearer tokens)."
        )
    return tokens


def get_valid_tokens() -> set[str]:
    """Return the set of currently valid tokens (cached)."""
    global _valid_tokens
    if _valid_tokens is None:
        _valid_tokens = _load_tokens()
    return _valid_tokens


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    """
    FastAPI dependency that validates the Bearer token.

    Returns the token string on success; raises 401 on failure.
    """
    token = credentials.credentials
    if token not in get_valid_tokens():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token.",
        )
    return token
