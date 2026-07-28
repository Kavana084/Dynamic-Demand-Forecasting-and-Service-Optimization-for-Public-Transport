"""
Entrypoint module for running the FastAPI app with Uvicorn.

This file normalizes `sys.path` so both of these commands resolve the same app:

- From project root: `uvicorn backend.main:app`
- From inside `backend/`: `uvicorn main:app`
"""

import os
import sys


BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

for path in (PROJECT_ROOT, BACKEND_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)


from backend.app.main import app  # type: ignore

# This file has been replaced to act as a proxy.
# By importing `app` from `app.main`, we ensure that if you run `uvicorn main:app`,
# it automatically serves the newly upgraded, modular backend (with GTFS dynamic routing)
# instead of the old monolithic Phase 1 backend.
