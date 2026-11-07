"""Environment parsing helpers with explicit failure behaviour."""

import os
from collections.abc import Iterable


def env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def env_bool(name: str, default: bool = False) -> bool:
    value = env(name)
    if value is None:
        return default
    normalized = value.casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value, got {value!r}.")


def env_int(name: str, default: int) -> int:
    value = env(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}.") from exc


def env_list(name: str, default: Iterable[str] = ()) -> list[str]:
    value = env(name)
    if value is None:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]
