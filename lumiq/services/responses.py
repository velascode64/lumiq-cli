from __future__ import annotations

from typing import Any


def success(**payload: Any) -> dict[str, Any]:
    return {"status": "success", **payload}


def error(code: str, message: str) -> dict[str, Any]:
    return {"status": "error", "error": {"code": code, "message": message}}