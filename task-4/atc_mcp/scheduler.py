"""Deterministic priority-aware scheduler.

The placer uses a **candidate-times** strategy: for each flight, build a
finite, sorted set of plausible start times (drawn from the boundaries of
every prior runway/gate/crew booking) and walk them in order until one
satisfies every constraint. This is obviously correct (we never skip a
feasible slot) and bounded in cost: O(N²) total in the number of placed
flights, which is plenty for the brief's scale.

The scheduler is pure: it consumes an immutable snapshot of flights plus
the configuration and returns assignments. Mutation of flight records is
the caller's responsibility — see :func:`schedule_airport`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from .config import AirportConfig, RunwaySpec
from .models import (
    Flight,
    FlightStatus,
    Operation,
    Schedule,
    ScheduledAssignment,
    TimelineEntry,
)


# ---------------------------------------------------------------------------
# Internal booking state
# ---------------------------------------------------------------------------


@dataclass
class _Booking:
    start: int
    end: int


@dataclass
class _RunwayBooking(_Booking):
    operation: Operation = "arrival"


@dataclass
class _BookingState:
    runways: dict[str, list[_RunwayBooking]] = field(default_factory=dict)
    gates: dict[str, list[_Booking]] = field(default_factory=dict)
    crew: list[_Booking] = field(default_factory=list)

    @classmethod
    def fresh(cls, cfg: AirportConfig) -> "_BookingState":
        return cls(
            runways={r.id: [] for r in cfg.runways},
            gates={g: [] for g in cfg.gates},
            crew=[],
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def schedule_airport(flights: Iterable[Flight], cfg: AirportConfig) -> Schedule:
    """Compute a fresh schedule for *flights*.

    Does **not** mutate the input flights. Returns a :class:`Schedule` that
    the caller is expected to write back onto the flight records.
    """
    active = [f for f in flights if f.status != FlightStatus.CANCELLED]

    by_id: dict[str, Flight] = {f.flight_number: f for f in active}
    unscheduled: dict[str, str] = {}

    # 1. Detect dependency cycles.
    for fid in _detect_cycles(by_id):
        unscheduled.setdefault(fid, "dependency cycle detected")

    # 2. Fail flights whose runway requirement exceeds capability.
    for fid, flight in by_id.items():
        if fid in unscheduled:
            continue
        if flight.min_runway_length > cfg.max_runway_length:
            unscheduled[fid] = (
                f"no suitable runway: requires {flight.min_runway_length}m "
                f"but max available is {cfg.max_runway_length}m"
            )

    # 3. Tier flights via Kahn's algorithm.
    tiers = _topological_tiers(by_id, blocked=set(unscheduled.keys()))

    # 4. Place flights tier by tier.
    bookings = _BookingState.fresh(cfg)
    assignments: dict[str, ScheduledAssignment] = {}

    for tier in tiers:
        tier_sorted = sorted(tier, key=lambda fid: by_id[fid].sort_key())
        for fid in tier_sorted:
            if fid in unscheduled:
                continue
            flight = by_id[fid]

            missing = _missing_dependency(flight, by_id, assignments, unscheduled)
            if missing is not None:
                unscheduled[fid] = missing
                continue

            earliest = _earliest_after_dependencies(flight, assignments, cfg)
            placed = _place_flight(flight, earliest, cfg, bookings)
            if placed is None:
                unscheduled[fid] = (
                    f"no slot found within horizon ({cfg.max_horizon_sec}s)"
                )
                continue
            assignments[fid] = placed

    # 5. Build the schedule output.
    timeline = [
        TimelineEntry(
            flight_number=fid,
            operation=by_id[fid].operation,
            runway=assn.runway,
            gate=assn.gate,
            start_sec=assn.runway_start_sec,
            end_sec=assn.runway_end_sec,
            finish_sec=assn.finish_sec,
            priority=by_id[fid].priority,
        )
        for fid, assn in assignments.items()
    ]
    timeline.sort(key=lambda e: (e.start_sec, e.runway, e.flight_number))

    completion = max((e.finish_sec for e in timeline), default=None)

    unscheduled_list = [
        {
            "flight_number": fid,
            "operation": by_id[fid].operation if fid in by_id else None,
            "priority": by_id[fid].priority if fid in by_id else None,
            "reason": reason,
        }
        for fid, reason in sorted(unscheduled.items())
    ]

    return Schedule(
        scheduled=timeline,
        unscheduled=unscheduled_list,
        completion_sec=completion,
    )


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _detect_cycles(by_id: dict[str, Flight]) -> set[str]:
    """Return the set of flight ids that participate in any dependency cycle."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {fid: WHITE for fid in by_id}
    in_cycle: set[str] = set()
    stack_path: list[str] = []

    def visit(fid: str) -> None:
        color[fid] = GRAY
        stack_path.append(fid)
        for dep in by_id[fid].dependencies:
            if dep not in by_id:
                continue
            if color[dep] == GRAY:
                idx = stack_path.index(dep)
                for node in stack_path[idx:]:
                    in_cycle.add(node)
            elif color[dep] == WHITE:
                visit(dep)
        color[fid] = BLACK
        stack_path.pop()

    for fid in sorted(by_id):
        if color[fid] == WHITE:
            visit(fid)
    return in_cycle


def _topological_tiers(
    by_id: dict[str, Flight], blocked: set[str]
) -> list[list[str]]:
    """Group flights into dependency tiers via Kahn's algorithm."""
    active = {fid for fid in by_id if fid not in blocked}
    remaining = dict(by_id)
    placed: set[str] = set()

    tiers: list[list[str]] = []
    while True:
        ready: list[str] = []
        for fid in sorted(active - placed):
            flight = remaining[fid]
            if all(
                dep not in active or dep in placed
                for dep in flight.dependencies
            ):
                ready.append(fid)
        if not ready:
            break
        tiers.append(ready)
        placed.update(ready)
    # Any leftover would belong to a cycle — already excluded by `blocked`.
    return tiers


def _missing_dependency(
    flight: Flight,
    by_id: dict[str, Flight],
    assignments: dict[str, ScheduledAssignment],
    unscheduled: dict[str, str],
) -> str | None:
    for dep in flight.dependencies:
        if dep not in by_id:
            return f"depends on unknown flight {dep}"
        if dep in unscheduled:
            return f"depends on unscheduled flight {dep}"
        if dep not in assignments:
            return f"dependency {dep} not yet scheduled"
    return None


def _earliest_after_dependencies(
    flight: Flight,
    assignments: dict[str, ScheduledAssignment],
    cfg: AirportConfig,
) -> int:
    if not flight.dependencies:
        return 0
    latest = 0
    for dep in flight.dependencies:
        assn = assignments[dep]
        latest = max(latest, assn.finish_sec + cfg.dependency_buffer_sec)
    return latest


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------


def _operation_duration(flight: Flight, cfg: AirportConfig) -> int:
    return (
        cfg.arrival_duration_sec
        if flight.operation == "arrival"
        else cfg.departure_duration_sec
    )


def _place_flight(
    flight: Flight,
    earliest_start: int,
    cfg: AirportConfig,
    bookings: _BookingState,
) -> ScheduledAssignment | None:
    """Search for the earliest-finish valid slot across all suitable runways.

    Returns the chosen assignment and commits the bookings as a side effect.
    """
    op_dur = _operation_duration(flight, cfg)
    turnaround = cfg.gate_turnaround_sec if flight.requires_gate else 0

    candidate_runways = sorted(
        (r for r in cfg.runways if r.length >= flight.min_runway_length),
        key=lambda r: (r.length, r.id),  # prefer the shortest suitable runway
    )
    if not candidate_runways:
        return None  # caught earlier; defensive

    best: ScheduledAssignment | None = None
    for runway in candidate_runways:
        slot = _find_earliest_slot(
            runway, flight, earliest_start, op_dur, turnaround, cfg, bookings
        )
        if slot is None:
            continue
        start, end, gate, finish = slot
        candidate = ScheduledAssignment(
            runway=runway.id,
            gate=gate,
            runway_start_sec=start,
            runway_end_sec=end,
            finish_sec=finish,
        )
        if best is None or candidate.finish_sec < best.finish_sec or (
            candidate.finish_sec == best.finish_sec
            and (candidate.runway_start_sec, candidate.runway) < (
                best.runway_start_sec,
                best.runway,
            )
        ):
            best = candidate

    if best is None:
        return None

    _commit(best, flight, cfg, bookings)
    return best


def _find_earliest_slot(
    runway: RunwaySpec,
    flight: Flight,
    earliest_start: int,
    op_dur: int,
    turnaround: int,
    cfg: AirportConfig,
    bookings: _BookingState,
) -> Optional[tuple[int, int, Optional[str], int]]:
    """Earliest valid runway start (and chosen gate) on *runway*, or ``None``.

    Strategy: enumerate every "boundary" time that could possibly unblock the
    flight, then walk those candidates in order and return the first one that
    satisfies every constraint.
    """
    candidates: set[int] = {earliest_start}

    # Runway boundaries: after each existing booking + buffer.
    for b in bookings.runways[runway.id]:
        sep = cfg.runway_buffer(b.operation, flight.operation)
        candidates.add(max(earliest_start, b.end + sep))

    # Crew boundaries: after each crew booking ends.
    for b in bookings.crew:
        candidates.add(max(earliest_start, b.end))

    # Gate boundaries: align the gate window with the end of a gate booking.
    if flight.requires_gate:
        for gate_id, gbookings in bookings.gates.items():
            for gb in gbookings:
                if flight.operation == "arrival":
                    # Gate window starts at runway_end; runway_end >= gb.end
                    candidates.add(max(earliest_start, gb.end - op_dur))
                else:
                    # Gate window ends at runway_start; runway_start >= gb.end + turnaround
                    candidates.add(max(earliest_start, gb.end + turnaround))

    for start in sorted(candidates):
        if start < earliest_start:
            continue
        end = start + op_dur
        if end > cfg.max_horizon_sec:
            break

        if not _runway_free(runway.id, start, end, flight.operation, cfg, bookings):
            continue
        if not _crew_available(bookings.crew, start, end, cfg):
            continue

        gate, finish = _select_gate(flight, start, end, turnaround, cfg, bookings)
        if flight.requires_gate and gate is None:
            continue
        if finish > cfg.max_horizon_sec:
            continue
        return start, end, gate, finish

    return None


def _runway_free(
    runway_id: str,
    start: int,
    end: int,
    op: Operation,
    cfg: AirportConfig,
    bookings: _BookingState,
) -> bool:
    for b in bookings.runways[runway_id]:
        sep = cfg.runway_buffer(b.operation, op)
        # We need either: end + sep <= b.start, OR start >= b.end + sep
        if not (end + sep <= b.start or start >= b.end + sep):
            return False
    return True


def _select_gate(
    flight: Flight,
    runway_start: int,
    runway_end: int,
    turnaround: int,
    cfg: AirportConfig,
    bookings: _BookingState,
) -> tuple[Optional[str], int]:
    """Pick the first available gate (deterministic order); return (gate, finish).

    ``finish`` is the moment the aircraft is considered "done" — used both as
    the schedule completion signal for the flight and as the anchor for any
    dependent operation's earliest start.
    """
    if not flight.requires_gate:
        return None, runway_end

    if flight.operation == "arrival":
        gw_start = runway_end
        gw_end = runway_end + turnaround
    else:
        gw_start = max(0, runway_start - turnaround)
        gw_end = runway_start

    for gate_id in cfg.gates:  # cfg.gates is an ordered tuple → deterministic
        if _gate_free(bookings.gates[gate_id], gw_start, gw_end):
            finish = gw_end if flight.operation == "arrival" else runway_end
            return gate_id, finish

    return None, runway_end


def _gate_free(gate_bookings: list[_Booking], start: int, end: int) -> bool:
    if start == end:
        return True
    for b in gate_bookings:
        if b.start < end and b.end > start:
            return False
    return True


def _crew_available(
    crew_bookings: list[_Booking], start: int, end: int, cfg: AirportConfig
) -> bool:
    overlapping = sum(1 for b in crew_bookings if b.start < end and b.end > start)
    return overlapping < cfg.ground_crew


def _commit(
    assn: ScheduledAssignment,
    flight: Flight,
    cfg: AirportConfig,
    bookings: _BookingState,
) -> None:
    """Mutate *bookings* to record the chosen assignment."""
    bookings.runways[assn.runway].append(
        _RunwayBooking(
            start=assn.runway_start_sec,
            end=assn.runway_end_sec,
            operation=flight.operation,
        )
    )
    bookings.runways[assn.runway].sort(key=lambda b: b.start)

    bookings.crew.append(_Booking(assn.runway_start_sec, assn.runway_end_sec))
    bookings.crew.sort(key=lambda b: b.start)

    if assn.gate is not None and flight.requires_gate:
        if flight.operation == "arrival":
            gw = _Booking(
                start=assn.runway_end_sec,
                end=assn.runway_end_sec + cfg.gate_turnaround_sec,
            )
        else:
            gw = _Booking(
                start=max(0, assn.runway_start_sec - cfg.gate_turnaround_sec),
                end=assn.runway_start_sec,
            )
        bookings.gates[assn.gate].append(gw)
        bookings.gates[assn.gate].sort(key=lambda b: b.start)


# ---------------------------------------------------------------------------
# Bottleneck analysis
# ---------------------------------------------------------------------------


def longest_dependency_chain(
    flights: dict[str, Flight], cfg: AirportConfig
) -> tuple[list[str], int]:
    """Return the longest active scheduled dependency chain.

    Chain length is the wall-clock elapsed time from the chain's first flight
    start to its last flight's finish (including dependency buffers and
    operation durations), computed from the generated schedule.
    """
    scheduled = {
        fid: f
        for fid, f in flights.items()
        if f.status == FlightStatus.SCHEDULED and f.assignment is not None
    }
    if not scheduled:
        return [], 0

    cache: dict[str, tuple[list[str], int]] = {}

    def longest_to(fid: str) -> tuple[list[str], int]:
        if fid in cache:
            return cache[fid]
        flight = scheduled[fid]
        assn = flight.assignment
        assert assn is not None
        # Use the flight's own operation duration on the runway as its chain length
        # contribution. ``finish_sec - runway_start_sec`` covers arrivals' gate window;
        # for departures this equals the runway duration.
        own_len = assn.finish_sec - assn.runway_start_sec
        best_path: list[str] = [fid]
        best_len: int = own_len
        for dep in flight.dependencies:
            if dep not in scheduled:
                continue
            sub_path, sub_len = longest_to(dep)
            candidate_len = sub_len + cfg.dependency_buffer_sec + own_len
            candidate_path = sub_path + [fid]
            if candidate_len > best_len or (
                candidate_len == best_len
                and tuple(candidate_path) < tuple(best_path)
            ):
                best_len = candidate_len
                best_path = candidate_path
        cache[fid] = (best_path, best_len)
        return cache[fid]

    best: tuple[list[str], int] = ([], 0)
    for fid in sorted(scheduled):
        path, length = longest_to(fid)
        if length > best[1] or (
            length == best[1] and tuple(path) < tuple(best[0])
        ):
            best = (path, length)
    return best
