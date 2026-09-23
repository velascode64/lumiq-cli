from __future__ import annotations

import json
from typing import Any


def dumps(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True)