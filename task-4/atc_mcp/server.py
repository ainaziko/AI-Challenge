"""MCP server entry point.

Wraps :class:`Airport` with FastMCP tools and resources.

Tools (callable by an MCP client):
* ``submit_flight``         — register a new arrival or departure.
* ``generate_schedule``     — recompute the schedule from current state.
* ``get_airport_status``    — structured operational snapshot.
* ``cancel_flight``         — cancel a flight and trigger re-evaluation.
* ``bottleneck_analysis``   — longest scheduled dependency chain.

Resources (readable URIs):
* ``atc://flights/queue``   — flight queue grouped by status.
* ``atc://runways/usage``   — per-runway availability + scheduled ops.
* ``atc://timeline``        — chronological list of scheduled operations.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from .airport import Airport, AirportError
from .config import ConfigError, load_config
from .models import FlightSubmission


def build_server() -> FastMCP:
    try:
        cfg = load_config()
    except ConfigError as exc:
        # Bubble up with a clear message so the host shows the misconfig.
        raise SystemExit(f"[atc-mcp] invalid configuration: {exc}") from exc

    airport = Airport(cfg)
    mcp = FastMCP("atc-mcp", instructions=_INSTRUCTIONS)

    # ---------------- tools ----------------

    @mcp.tool()
    def submit_flight(
        flight_number: str,
        operation: str,
        priority: str = "medium",
        dependencies: list[str] | None = None,
        min_runway_length: int = 0,
        requires_gate: bool = True,
    ) -> dict[str, Any]:
        """Submit a new arrival or departure to the queue.

        ``operation`` must be ``"arrival"`` or ``"departure"``.
        ``priority`` must be ``"high"``, ``"medium"`` or ``"low"``.
        ``dependencies`` lists flight numbers that must complete first.
        ``min_runway_length`` is the minimum runway length (meters) required.
        """
        try:
            payload = FlightSubmission(
                flight_number=flight_number,
                operation=operation,  # type: ignore[arg-type]
                priority=priority,  # type: ignore[arg-type]
                dependencies=dependencies or [],
                min_runway_length=min_runway_length,
                requires_gate=requires_gate,
            )
        except ValidationError as exc:
            return {"ok": False, "error": "invalid_payload", "details": exc.errors()}
        try:
            flight = airport.submit(payload)
        except AirportError as exc:
            return {"ok": False, "error": str(exc)}
        return {
            "ok": True,
            "flight_number": flight.flight_number,
            "status": flight.status.value,
            "note": "schedule invalidated — call generate_schedule to refresh",
        }

    @mcp.tool()
    def generate_schedule() -> dict[str, Any]:
        """Recompute the entire schedule from the current flight queue.

        Returns the new schedule (scheduled timeline + unscheduled flights
        with reasons) and the completion time of the airport plan.
        """
        result = airport.generate_schedule()
        return {
            "ok": True,
            "completion_sec": result.completion_sec,
            "scheduled_count": len(result.scheduled),
            "unscheduled_count": len(result.unscheduled),
            "scheduled": [e.model_dump() for e in result.scheduled],
            "unscheduled": result.unscheduled,
        }

    @mcp.tool()
    def get_airport_status() -> dict[str, Any]:
        """Return structured airport status (counts, resource usage, blockers)."""
        return airport.status_snapshot()

    @mcp.tool()
    def cancel_flight(flight_number: str) -> dict[str, Any]:
        """Cancel a flight. Dependent flights will be re-evaluated on next schedule."""
        try:
            flight = airport.cancel(flight_number)
        except AirportError as exc:
            return {"ok": False, "error": str(exc)}
        return {
            "ok": True,
            "flight_number": flight.flight_number,
            "status": flight.status.value,
            "note": "schedule invalidated — call generate_schedule to refresh",
        }

    @mcp.tool()
    def bottleneck_analysis() -> dict[str, Any]:
        """Identify the longest active scheduled dependency chain.

        The result includes the ordered chain of flight numbers and the
        elapsed wall-clock duration based on the generated schedule
        (operation durations + configured dependency buffer).
        """
        return airport.bottleneck()

    # ---------------- resources ------------

    @mcp.resource("atc://flights/queue")
    def flight_queue_resource() -> str:
        """All flights grouped by status (queued/scheduled/unscheduled/cancelled)."""
        return _json(airport.queue_snapshot())

    @mcp.resource("atc://runways/usage")
    def runway_usage_resource() -> str:
        """Per-runway capacity, length and ordered scheduled operations."""
        return _json(airport.runway_snapshot())

    @mcp.resource("atc://timeline")
    def timeline_resource() -> str:
        """Chronological timeline of scheduled airport operations."""
        return _json(airport.timeline_snapshot())

    return mcp


def _json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=False, default=str)


_INSTRUCTIONS = """\
This MCP server coordinates flight operations at a single airport.

Typical workflow:
1. Call `submit_flight` once per arrival/departure. Provide dependencies and
   `min_runway_length` if relevant.
2. Call `generate_schedule` to compute a deterministic plan. Subsequent
   submissions invalidate the plan — call this again to refresh.
3. Read `atc://timeline` for the chronological plan and `atc://flights/queue`
   for the per-flight state with reasons for any unscheduled flights.
4. Use `bottleneck_analysis` to surface the longest dependency chain.
5. Use `cancel_flight` to remove a flight; re-run `generate_schedule` to
   re-evaluate dependents.

Airport limits (runways, gates, ground crew, buffers, horizon) are loaded
from environment variables at startup. See `.env.example` for the full list.
"""


def main() -> None:
    server = build_server()
    server.run()


if __name__ == "__main__":
    main()
