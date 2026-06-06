"""Pytest bootstrap for backend tests.

Ensures the backend package root is importable as `app.*` when tests are run
from the `backend/` directory or by CI.
"""

from __future__ import annotations

import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
