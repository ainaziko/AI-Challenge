"""Airport state — the single source of truth for the MCP server.

State is kept in-process. The MCP server is typically restarted per session
so a process-local store is sufficient for the brief; persistence could be
added later by serialising :class:`Airport`.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Any

from .config import AirportConfig
from .models import (
    Flight,
    FlightStatus,
    FlightSubmission,
    PRIORITY_RANK,
    Schedule,
)
from .scheduler import longest_dependency_chain, schedule_airport


class AirportError(Exception):
    """Raised for caller-facing errors (duplicate ids, unknown flights, ...)."""


class Airport:
    """Mutable airport state, thread-safe for concurrent MCP calls."""

    def __init__(self, cfg: AirportConfig) -> None:
        self._cfg = cfg
        self._lock = threading.RLock()
        self._flights: dict[str, Flight] = {}
        self._counter: int = 0
        self._last_schedule: Schedule | None = None

    # ---------------- config ----------------

    @property
    def config(self) -> AirportConfig:
        return self._cfg

    # ---------------- mutations -------------

    def submit(self, payload: FlightSubmission) -> Flight:
        with self._lock:
            if payload.flight_number in self._flights:
                raise AirportError(
                    f"flight {payload.flight_number} already submitted"
                )
            self._counter += 1
            flight = Flight(
                flight_number=payload.flight_number,
                operation=payload.operation,
                priority=payload.priority,
                dependencies=list(payload.dependencies),
                min_runway_length=payload.min_runway_length,
                requires_gate=payload.requires_gate,
                submitted_seq=self._counter,
                status=FlightStatus.QUEUED,
            )
            self._flights[flight.flight_number] = flight
            # Invalidate prior schedule — caller must regenerate to see new state.
            self._invalidate_schedule()
            return flight

    def cancel(self, flight_number: str) -> Flight:
        flight_number = flight_number.strip().upper()
        with self._lock:
            flight = self._flights.get(flight_number)
            if flight is None:
                raise AirportError(f"unknown flight {flight_number}")
            if flight.status == FlightStatus.CANCELLED:
                return flight
            flight.status = FlightStatus.CANCELLED
            flight.assignment = None
            flight.unschedulable_reason = "cancelled"
            self._invalidate_schedule()
            return flight

    def generate_schedule(self) -> Schedule:
        """Compute a fresh schedule and write assignments back onto flights."""
        with self._lock:
            # Reset per-flight scheduling state for all non-cancelled flights.
            for flight in self._flights.values():
                if flight.status == FlightStatus.CANCELLED:
                    continue
                flight.status = FlightStatus.QUEUED
                flight.assignment = None
                flight.unschedulable_reason = None

            result = schedule_airport(self._flights.values(), self._cfg)

            scheduled_ids: set[str] = set()
            for entry in result.scheduled:
                flight = self._flights[entry.flight_number]
                flight.status = FlightStatus.SCHEDULED
                flight.assignment = _entry_to_assignment(entry)
                scheduled_ids.add(entry.flight_number)

            for u in result.unscheduled:
                fid = u["flight_number"]
                if fid in self._flights and fid not in scheduled_ids:
                    flight = self._flights[fid]
                    if flight.status != FlightStatus.CANCELLED:
                        flight.status = FlightStatus.UNSCHEDULED
                    flight.unschedulable_reason = u.get("reason")

            self._last_schedule = result
            return result

    # ---------------- queries ---------------

    def list_flights(self) -> list[Flight]:
        with self._lock:
            return sorted(
                self._flights.values(),
                key=lambda f: (f.submitted_seq, f.flight_number),
            )

    def get_flight(self, flight_number: str) -> Flight:
        flight_number = flight_number.strip().upper()
        with self._lock:
            flight = self._flights.get(flight_number)
            if flight is None:
                raise AirportError(f"unknown flight {flight_number}")
            return flight

    def queue_snapshot(self) -> dict[str, Any]:
        with self._lock:
            grouped: dict[str, list[dict[str, Any]]] = {
                "queued": [],
                "scheduled": [],
                "unscheduled": [],
                "cancelled": [],
            }
            for flight in self.list_flights():
                bucket = grouped[flight.status.value]
                bucket.append(_flight_to_dict(flight, self._cfg))
            return {
                "total": len(self._flights),
                "by_status": {k: len(v) for k, v in grouped.items()},
                "flights": grouped,
            }

    def runway_snapshot(self) -> dict[str, Any]:
        with self._lock:
            usage: list[dict[str, Any]] = []
            scheduled = [
                f
                for f in self._flights.values()
                if f.status == FlightStatus.SCHEDULED and f.assignment
            ]
            for runway in self._cfg.runways:
                ops = sorted(
                    (
                        {
                            "flight_number": f.flight_number,
                            "operation": f.operation,
                            "priority": f.priority,
                            "start_sec": f.assignment.runway_start_sec,  # type: ignore[union-attr]
                            "end_sec": f.assignment.runway_end_sec,  # type: ignore[union-attr]
                            "start_iso": _iso(self._cfg, f.assignment.runway_start_sec),  # type: ignore[union-attr]
                            "end_iso": _iso(self._cfg, f.assignment.runway_end_sec),  # type: ignore[union-attr]
                        }
                        for f in scheduled
                        if f.assignment and f.assignment.runway == runway.id
                    ),
                    key=lambda o: o["start_sec"],
                )
                busy_sec = sum(o["end_sec"] - o["start_sec"] for o in ops)
                usage.append(
                    {
                        "runway_id": runway.id,
                        "length_m": runway.length,
                        "operations": ops,
                        "busy_seconds": busy_sec,
                    }
                )
            return {
                "runways": usage,
                "horizon_sec": self._cfg.max_horizon_sec,
                "epoch_iso": self._cfg.epoch.isoformat(),
            }

    def timeline_snapshot(self) -> dict[str, Any]:
        with self._lock:
            entries: list[dict[str, Any]] = []
            for f in self._flights.values():
                if f.status != FlightStatus.SCHEDULED or f.assignment is None:
                    continue
                entries.append(
                    {
                        "flight_number": f.flight_number,
                        "operation": f.operation,
                        "priority": f.priority,
                        "runway": f.assignment.runway,
                        "gate": f.assignment.gate,
                        "start_sec": f.assignment.runway_start_sec,
                        "end_sec": f.assignment.runway_end_sec,
                        "finish_sec": f.assignment.finish_sec,
                        "start_iso": _iso(self._cfg, f.assignment.runway_start_sec),
                        "end_iso": _iso(self._cfg, f.assignment.runway_end_sec),
                        "finish_iso": _iso(self._cfg, f.assignment.finish_sec),
                        "depends_on": list(f.dependencies),
                    }
                )
            entries.sort(key=lambda e: (e["start_sec"], e["runway"], e["flight_number"]))
            return {
                "epoch_iso": self._cfg.epoch.isoformat(),
                "entries": entries,
            }

    def status_snapshot(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {s.value: 0 for s in FlightStatus}
            by_op: dict[str, int] = {"arrival": 0, "departure": 0}
            unscheduled_details: list[dict[str, Any]] = []
            for f in self._flights.values():
                by_status[f.status.value] += 1
                by_op[f.operation] += 1
                if f.status == FlightStatus.UNSCHEDULED:
                    unscheduled_details.append(
                        {
                            "flight_number": f.flight_number,
                            "operation": f.operation,
                            "priority": f.priority,
                            "reason": f.unschedulable_reason,
                        }
                    )
            scheduled = [
                f for f in self._flights.values()
                if f.status == FlightStatus.SCHEDULED and f.assignment
            ]
            runways_in_use = {f.assignment.runway for f in scheduled if f.assignment}
            gates_in_use = {
                f.assignment.gate
                for f in scheduled
                if f.assignment and f.assignment.gate
            }
            crew_peak = _peak_concurrent(
                [
                    (f.assignment.runway_start_sec, f.assignment.runway_end_sec)
                    for f in scheduled
                    if f.assignment
                ]
            )
            completion = (
                self._last_schedule.completion_sec if self._last_schedule else None
            )
            constraints: list[str] = []
            if len(runways_in_use) >= len(self._cfg.runways):
                constraints.append("all runways have at least one scheduled operation")
            if len(gates_in_use) >= len(self._cfg.gates):
                constraints.append("all gates have at least one scheduled occupation")
            if crew_peak >= self._cfg.ground_crew:
                constraints.append("ground crew demand reached configured capacity")

            return {
                "flight_counts": {
                    "by_status": by_status,
                    "by_operation": by_op,
                    "total": len(self._flights),
                },
                "resources": {
                    "runways": {
                        "configured": len(self._cfg.runways),
                        "with_scheduled_ops": len(runways_in_use),
                    },
                    "gates": {
                        "configured": len(self._cfg.gates),
                        "with_scheduled_ops": len(gates_in_use),
                    },
                    "ground_crew": {
                        "configured": self._cfg.ground_crew,
                        "peak_concurrent_use": crew_peak,
                    },
                },
                "constraints": constraints,
                "unscheduled_flights": unscheduled_details,
                "schedule_completion_sec": completion,
                "schedule_completion_iso": (
                    _iso(self._cfg, completion) if completion is not None else None
                ),
            }

    def bottleneck(self) -> dict[str, Any]:
        with self._lock:
            chain, total = longest_dependency_chain(self._flights, self._cfg)
            if not chain:
                return {
                    "chain": [],
                    "total_duration_sec": 0,
                    "description": "no scheduled dependency chain present",
                }
            description = (
                f"longest active scheduled dependency chain spans {len(chain)} "
                f"flights and {total} seconds end to end (including buffers)"
            )
            return {
                "chain": chain,
                "total_duration_sec": total,
                "description": description,
            }

    # ---------------- internals -------------

    def _invalidate_schedule(self) -> None:
        self._last_schedule = None
        for f in self._flights.values():
            if f.status == FlightStatus.SCHEDULED:
                f.status = FlightStatus.QUEUED
                f.assignment = None
                f.unschedulable_reason = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso(cfg: AirportConfig, offset_sec: int) -> str:
    return (cfg.epoch + timedelta(seconds=offset_sec)).isoformat()


def _flight_to_dict(flight: Flight, cfg: AirportConfig) -> dict[str, Any]:
    base: dict[str, Any] = {
        "flight_number": flight.flight_number,
        "operation": flight.operation,
        "priority": flight.priority,
        "dependencies": list(flight.dependencies),
        "min_runway_length": flight.min_runway_length,
        "requires_gate": flight.requires_gate,
        "submitted_seq": flight.submitted_seq,
        "status": flight.status.value,
    }
    if flight.assignment is not None:
        base["assignment"] = {
            "runway": flight.assignment.runway,
            "gate": flight.assignment.gate,
            "runway_start_sec": flight.assignment.runway_start_sec,
            "runway_end_sec": flight.assignment.runway_end_sec,
            "finish_sec": flight.assignment.finish_sec,
            "runway_start_iso": _iso(cfg, flight.assignment.runway_start_sec),
            "runway_end_iso": _iso(cfg, flight.assignment.runway_end_sec),
            "finish_iso": _iso(cfg, flight.assignment.finish_sec),
        }
    if flight.unschedulable_reason:
        base["reason"] = flight.unschedulable_reason
    return base


def _entry_to_assignment(entry) -> Any:  # noqa: ANN401
    from .models import ScheduledAssignment

    return ScheduledAssignment(
        runway=entry.runway,
        gate=entry.gate,
        runway_start_sec=entry.start_sec,
        runway_end_sec=entry.end_sec,
        finish_sec=entry.finish_sec,
    )


def _peak_concurrent(intervals: list[tuple[int, int]]) -> int:
    events: list[tuple[int, int]] = []
    for s, e in intervals:
        events.append((s, +1))
        events.append((e, -1))
    events.sort()
    peak = 0
    cur = 0
    for _, delta in events:
        cur += delta
        peak = max(peak, cur)
    return peak
