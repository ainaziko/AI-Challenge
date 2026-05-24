"""Airport configuration loaded from environment variables.

All limits are validated at construction time. If the configuration is invalid
the server fails fast on startup with an explanatory message.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone


class ConfigError(ValueError):
    """Raised when the environment configuration is invalid."""


@dataclass(frozen=True)
class RunwaySpec:
    id: str
    length: int  # meters


@dataclass(frozen=True)
class AirportConfig:
    runways: tuple[RunwaySpec, ...]
    gates: tuple[str, ...]
    ground_crew: int

    runway_buffer_takeoff_sec: int
    runway_buffer_landing_sec: int
    runway_buffer_mixed_sec: int

    arrival_duration_sec: int
    departure_duration_sec: int
    gate_turnaround_sec: int

    dependency_buffer_sec: int
    max_horizon_sec: int

    epoch: datetime = field(default_factory=lambda: _utc_midnight_today())

    # ----- convenience -----
    @property
    def max_runway_length(self) -> int:
        return max((r.length for r in self.runways), default=0)

    def runway_buffer(self, prev_op: str, next_op: str) -> int:
        """Required separation between two consecutive runway operations.

        ``arrival``/``departure`` are accepted. Mixed pair → mixed buffer.
        """
        if prev_op == next_op == "departure":
            return self.runway_buffer_takeoff_sec
        if prev_op == next_op == "arrival":
            return self.runway_buffer_landing_sec
        return self.runway_buffer_mixed_sec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_midnight_today() -> datetime:
    now = datetime.now(tz=timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _require_int(name: str, value: str | None, *, minimum: int = 0) -> int:
    if value is None or value.strip() == "":
        raise ConfigError(f"{name} must be set")
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {value!r}") from exc
    if parsed < minimum:
        raise ConfigError(f"{name} must be >= {minimum}, got {parsed}")
    return parsed


def _parse_runways(raw: str | None) -> tuple[RunwaySpec, ...]:
    if not raw or not raw.strip():
        raise ConfigError("ATC_RUNWAYS must list at least one runway, e.g. R1:3000")
    specs: list[RunwaySpec] = []
    seen: set[str] = set()
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            raise ConfigError(
                f"ATC_RUNWAYS entry {chunk!r} is malformed; expected ID:length"
            )
        rid, length_str = chunk.split(":", 1)
        rid = rid.strip()
        if not rid:
            raise ConfigError("ATC_RUNWAYS contains an entry with empty id")
        if rid in seen:
            raise ConfigError(f"ATC_RUNWAYS contains duplicate id {rid!r}")
        try:
            length = int(length_str.strip())
        except ValueError as exc:
            raise ConfigError(
                f"ATC_RUNWAYS entry {chunk!r} has non-integer length"
            ) from exc
        if length <= 0:
            raise ConfigError(
                f"ATC_RUNWAYS entry {chunk!r} must declare positive length"
            )
        specs.append(RunwaySpec(id=rid, length=length))
        seen.add(rid)
    if not specs:
        raise ConfigError("ATC_RUNWAYS must list at least one runway")
    return tuple(specs)


def _parse_gates(raw: str | None) -> tuple[str, ...]:
    if not raw or not raw.strip():
        raise ConfigError("ATC_GATES must be set (integer count or comma-separated ids)")
    raw = raw.strip()
    # If it is purely numeric, treat as count and auto-name.
    if raw.isdigit():
        count = int(raw)
        if count <= 0:
            raise ConfigError("ATC_GATES count must be positive")
        return tuple(f"G{i}" for i in range(1, count + 1))
    ids: list[str] = []
    seen: set[str] = set()
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if chunk in seen:
            raise ConfigError(f"ATC_GATES contains duplicate id {chunk!r}")
        ids.append(chunk)
        seen.add(chunk)
    if not ids:
        raise ConfigError("ATC_GATES must list at least one gate id")
    return tuple(ids)


def _parse_epoch(raw: str | None) -> datetime:
    if not raw or not raw.strip():
        return _utc_midnight_today()
    raw = raw.strip()
    # Accept trailing Z by converting to +00:00 for fromisoformat compatibility.
    iso = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError as exc:
        raise ConfigError(
            f"ATC_EPOCH_ISO must be ISO-8601, got {raw!r}"
        ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_config(env: dict[str, str] | None = None) -> AirportConfig:
    """Load and validate ``AirportConfig`` from environment variables.

    Pass ``env`` to override ``os.environ`` (useful for tests).
    """
    src = env if env is not None else os.environ

    cfg = AirportConfig(
        runways=_parse_runways(src.get("ATC_RUNWAYS")),
        gates=_parse_gates(src.get("ATC_GATES")),
        ground_crew=_require_int("ATC_GROUND_CREW", src.get("ATC_GROUND_CREW"), minimum=1),
        runway_buffer_takeoff_sec=_require_int(
            "ATC_RUNWAY_BUFFER_TAKEOFF_SEC", src.get("ATC_RUNWAY_BUFFER_TAKEOFF_SEC")
        ),
        runway_buffer_landing_sec=_require_int(
            "ATC_RUNWAY_BUFFER_LANDING_SEC", src.get("ATC_RUNWAY_BUFFER_LANDING_SEC")
        ),
        runway_buffer_mixed_sec=_require_int(
            "ATC_RUNWAY_BUFFER_MIXED_SEC", src.get("ATC_RUNWAY_BUFFER_MIXED_SEC")
        ),
        arrival_duration_sec=_require_int(
            "ATC_ARRIVAL_DURATION_SEC", src.get("ATC_ARRIVAL_DURATION_SEC"), minimum=1
        ),
        departure_duration_sec=_require_int(
            "ATC_DEPARTURE_DURATION_SEC", src.get("ATC_DEPARTURE_DURATION_SEC"), minimum=1
        ),
        gate_turnaround_sec=_require_int(
            "ATC_GATE_TURNAROUND_SEC", src.get("ATC_GATE_TURNAROUND_SEC"), minimum=1
        ),
        dependency_buffer_sec=_require_int(
            "ATC_DEPENDENCY_BUFFER_SEC", src.get("ATC_DEPENDENCY_BUFFER_SEC")
        ),
        max_horizon_sec=_require_int(
            "ATC_MAX_HORIZON_SEC", src.get("ATC_MAX_HORIZON_SEC"), minimum=1
        ),
        epoch=_parse_epoch(src.get("ATC_EPOCH_ISO")),
    )
    return cfg
