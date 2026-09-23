from __future__ import annotations

from typing import Any


def lines(response: dict[str, Any]) -> list[str]:
    if response.get("status") == "error":
        return [f"Error: {response['error']['message']}"]
    if "strategies" in response:
        return ["  ".join(f"{key}={value}" for key, value in item.items()) for item in response["strategies"]]
    if "runs" in response:
        if not response["runs"]:
            return ["No hay ejecuciones registradas."]
        return ["  ".join(f"{key}={value}" for key, value in item.items()) for item in response["runs"]]
    if "logs" in response:
        return [response["logs"]]
    payload = {key: value for key, value in response.items() if key != "status"}
    return [f"{key}: {value}" for key, value in payload.items()]