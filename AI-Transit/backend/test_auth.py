import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import Request, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.exceptions import ServiceException
from app.api_routes import verify_admin, login
from app.validators import LoginRequest

class MockRequest:
    pass

async def run_tests():
    print("--- 1. Testing Legacy X-Admin-Token Auth ---")
    try:
        user = verify_admin(x_admin_token="transit_admin_secret", auth=None)
        print(f"Legacy Auth Success! User: {user}")
    except Exception as e:
        print(f"Legacy Auth Failed: {str(e)}")

    print("\n--- 2. Testing JWT Login (Admin) ---")
    try:
        login_req = LoginRequest(username="admin", password="admin123")
        token_resp = login(login_req)
        print(f"Login Success! Role: {token_resp.role}")
        access_token = token_resp.access_token
    except Exception as e:
        print(f"Login Failed: {str(e)}")
        access_token = None

    if access_token:
        print("\n--- 3. Testing JWT Auth Access ---")
        try:
            auth_cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials=access_token)
            # x_admin_token is None here, to test pure JWT
            user = verify_admin(x_admin_token=None, auth=auth_cred)
            print(f"JWT Auth Success! User: {user}")
        except Exception as e:
            print(f"JWT Auth Failed: {str(e)}")

    print("\n--- 4. Testing RBAC Failure (Viewer Role) ---")
    try:
        viewer_req = LoginRequest(username="viewer", password="viewer123")
        viewer_token = login(viewer_req).access_token
        auth_cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials=viewer_token)
        try:
            verify_admin(x_admin_token=None, auth=auth_cred)
            print("JWT Auth Failed: Viewer was incorrectly granted access.")
        except HTTPException as e:
            print(f"RBAC Success! Viewer correctly denied with: {e.detail}")
    except Exception as e:
        print(f"RBAC Logic Error: {str(e)}")

asyncio.run(run_tests())
