from __future__ import annotations

from typing import Any, Dict


def success_response(data: Any) -> Dict[str, Any]:
    return {"status": "success", "data": data}


def error_response(message: str, error_code: str) -> Dict[str, Any]:
    return {"status": "error", "message": message, "error_code": error_code}

