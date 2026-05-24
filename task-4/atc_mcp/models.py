"""Flight and schedule data models."""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums / literals
# ---------------------------------------------------------------------------

Operation = Literal["arrival", "departure"]
Priority = Literal["high", "medium", "low"]

# Numeric rank for ordering. Lower = scheduled first.
PRIORITY_RANK: dict[str, int] = {"high": 0, "medium": 1, "low": 2}


class FlightStatus(str, Enum):
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    UNSCHEDULED = "unscheduled"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


class FlightSubmission(BaseModel):
    """Payload accepted by the ``submit_flight`` tool."""

    flight_number: str = Field(..., min_length=1, max_length=16)
    operation: Operation
    priority: Priority = "medium"
    dependencies: list[str] = Field(default_factory=list)
    min_runway_length: int = Field(
        default=0, ge=0, description="Minimum runway length (meters) required."
    )
    requires_gate: bool = True

    @field_validator("flight_number")
    @classmethod
    def _normalize_flight_number(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("flight_number cannot be empty")
        return v

    @field_validator("dependencies")
    @classmethod
    def _normalize_deps(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for dep in v:
            dep = dep.strip().upper()
            if not dep:
                continue
            if dep in seen:
                continue
            out.append(dep)
            seen.add(dep)
        return out


# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------


class ScheduledAssignment(BaseModel):
    """Concrete time + resource assignment for a scheduled flight."""

    runway: str
    gate: Optional[str]
    runway_start_sec: int  # offset from airport epoch
    runway_end_sec: int
    finish_sec: int  # gate-released time (relevant for dependencies)


class Flight(BaseModel):
    """Mutable flight record kept in the airport state."""

    flight_number: str
    operation: Operation
    priority: Priority
    dependencies: list[str] = Field(default_factory=list)
    min_runway_length: int = 0
    requires_gate: bool = True
    submitted_seq: int = 0  # monotonically increasing submission counter
    status: FlightStatus = FlightStatus.QUEUED
    assignment: Optional[ScheduledAssignment] = None
    unschedulable_reason: Optional[str] = None

    def priority_rank(self) -> int:
        return PRIORITY_RANK[self.priority]

    def sort_key(self) -> tuple[int, int, str]:
        """Stable, deterministic ordering for the scheduler."""
        return (self.priority_rank(), self.submitted_seq, self.flight_number)


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


class TimelineEntry(BaseModel):
    flight_number: str
    operation: Operation
    runway: str
    gate: Optional[str]
    start_sec: int
    end_sec: int
    finish_sec: int
    priority: Priority


class Schedule(BaseModel):
    """Result of a scheduling pass."""

    scheduled: list[TimelineEntry] = Field(default_factory=list)
    unscheduled: list[dict] = Field(default_factory=list)
    completion_sec: Optional[int] = None  # latest finish_sec across scheduled flights


class BottleneckChain(BaseModel):
    flights: list[str]
    total_duration_sec: int
    description: str
