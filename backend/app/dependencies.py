"""
Shared FastAPI auth dependencies.

Moved out of app/api_routes.py so any router (admin, fleet, ai, etc.) can
require authentication without importing the entire api_routes module.
"""
import os
from fastapi import Header, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .services.auth_service import decode_access_token
from .logger import app_logger

security = HTTPBearer(auto_error=False)

_DEFAULT_ADMIN_TOKEN = "transit_admin_secret"


def verify_admin(
    x_admin_token: str = Header(None),
    auth: HTTPAuthorizationCredentials = Depends(security),
):
    """Require the caller to be an Admin (or Operator) via legacy header token or JWT."""
    admin_token = os.getenv("ADMIN_TOKEN", _DEFAULT_ADMIN_TOKEN)
    if admin_token == _DEFAULT_ADMIN_TOKEN:
        app_logger.warning(
            "ADMIN_TOKEN is not set — falling back to the default legacy admin token. "
            "Set ADMIN_TOKEN in the environment before deploying to production."
        )

    # 1. Legacy header-token check
    if x_admin_token and x_admin_token == admin_token:
        return {"role": "Admin", "username": "legacy_admin"}

    # 2. JWT check
    if auth and auth.credentials:
        payload = decode_access_token(auth.credentials)
        if payload and payload.get("role") in ["Admin", "Operator"]:
            return payload

    raise HTTPException(status_code=401, detail="Unauthorized")


def get_current_user_optional(auth: HTTPAuthorizationCredentials = Depends(security)):
    """Returns decoded JWT payload if a valid Bearer token is present, else None."""
    if auth and auth.credentials:
        return decode_access_token(auth.credentials)
    return None


def require_passenger(auth: HTTPAuthorizationCredentials = Depends(security)):
    """Requires a valid JWT (any role). Raises 401 on failure."""
    if not auth or not auth.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_access_token(auth.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload