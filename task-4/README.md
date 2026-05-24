# Task 4 — ATC MCP Server

A Model Context Protocol server that coordinates flight operations at a single
airport. It accepts arrivals and departures, schedules them across configured
runways and gates while respecting priorities, dependencies, and separation
buffers, and exposes airport state to AI clients through MCP tools and
resources.

## Quick start

```bash
cd task-4

# 1. Install
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env (or just `set -a; source .env; set +a` to export the vars)

# 3. Run the server (stdio transport — connect from an MCP client)
python -m atc_mcp
```

The server speaks MCP over **stdio**. Any MCP-compatible client can connect.

### Connecting from Claude Desktop

Add the server to `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) — adjust the path to your checkout:

```json
{
  "mcpServers": {
    "atc": {
      "command": "/absolute/path/to/task-4/.venv/bin/python",
      "args": ["-m", "atc_mcp"],
      "env": {
        "ATC_RUNWAYS": "R1:3000,R2:4000,R3:2500",
        "ATC_GATES": "4",
        "ATC_GROUND_CREW": "8",
        "ATC_RUNWAY_BUFFER_TAKEOFF_SEC": "120",
        "ATC_RUNWAY_BUFFER_LANDING_SEC": "90",
        "ATC_RUNWAY_BUFFER_MIXED_SEC": "180",
        "ATC_ARRIVAL_DURATION_SEC": "300",
        "ATC_DEPARTURE_DURATION_SEC": "300",
        "ATC_GATE_TURNAROUND_SEC": "2400",
        "ATC_DEPENDENCY_BUFFER_SEC": "600",
        "ATC_MAX_HORIZON_SEC": "86400"
      }
    }
  }
}
```

Restart Claude Desktop. The ATC tools and resources will appear in the MCP
panel.

### Quick smoke test from the CLI

```bash
python - <<'PY'
from atc_mcp.airport import Airport
from atc_mcp.config import load_config
from atc_mcp.models import FlightSubmission

airport = Airport(load_config())
airport.submit(FlightSubmission(flight_number="QF1", operation="arrival", priority="high"))
airport.submit(FlightSubmission(flight_number="QF2", operation="departure", dependencies=["QF1"]))
print(airport.generate_schedule().model_dump_json(indent=2))
PY
```

## Configuration

Every limit comes from an environment variable. Invalid or missing values
cause the server to fail at startup with a descriptive `[atc-mcp] invalid
configuration: ...` message.

| Variable | Type | Description |
| --- | --- | --- |
| `ATC_RUNWAYS` | `ID:length_m,...` | Runways. Length in meters; used to match `min_runway_length` requirements. |
| `ATC_GATES` | `int` or `G1,G2,...` | Either a count (auto-named `G1..Gn`) or an explicit list of gate ids. |
| `ATC_GROUND_CREW` | `int >= 1` | Number of crew units. Each runway operation consumes 1 unit while in progress. |
| `ATC_RUNWAY_BUFFER_TAKEOFF_SEC` | `int` | Separation between two consecutive departures on the same runway. |
| `ATC_RUNWAY_BUFFER_LANDING_SEC` | `int` | Separation between two consecutive arrivals on the same runway. |
| `ATC_RUNWAY_BUFFER_MIXED_SEC` | `int` | Separation between an arrival ↔ departure pair on the same runway. |
| `ATC_ARRIVAL_DURATION_SEC` | `int >= 1` | Runway occupation time for one arrival. |
| `ATC_DEPARTURE_DURATION_SEC` | `int >= 1` | Runway occupation time for one departure. |
| `ATC_GATE_TURNAROUND_SEC` | `int >= 1` | Gate occupation time per flight (after an arrival or before a departure). |
| `ATC_DEPENDENCY_BUFFER_SEC` | `int` | Minimum gap between a dependency's finish and the dependent flight's start. |
| `ATC_MAX_HORIZON_SEC` | `int >= 1` | Flights that cannot be placed inside this window are reported as unscheduled. |
| `ATC_EPOCH_ISO` | ISO-8601 | Optional. Base time for ISO timestamps in responses. Defaults to today's UTC midnight. |

## Tool reference

All tools accept and return JSON; errors are surfaced as `{"ok": false, "error": "..."}`.

| Tool | Purpose | Key arguments |
| --- | --- | --- |
| `submit_flight` | Register a new arrival/departure. Invalidates the current schedule. | `flight_number`, `operation` (`arrival`/`departure`), `priority` (`high`/`medium`/`low`), `dependencies`, `min_runway_length`, `requires_gate` |
| `generate_schedule` | Recompute the full schedule from the current queue + config. | _none_ |
| `get_airport_status` | Operational snapshot — counts, resource usage, constraints, completion time. | _none_ |
| `cancel_flight` | Cancel a flight. Dependents become unscheduled on next `generate_schedule`. | `flight_number` |
| `bottleneck_analysis` | Longest active scheduled dependency chain. Returns chain + total seconds. | _none_ |

## Resource reference

Resources are read-only JSON. Re-read them after any state change.

| URI | Contents |
| --- | --- |
| `atc://flights/queue` | All flights grouped by status (`queued`, `scheduled`, `unscheduled`, `cancelled`) with per-flight detail. |
| `atc://runways/usage` | Per-runway capacity, declared length, ordered scheduled operations, total busy seconds. |
| `atc://timeline` | Chronological list of scheduled operations with ISO + offset timestamps and dependency edges. |

## Scheduling rules in plain English

1. **Cancel first, then dependents.** Cancelled flights are excluded. Anything
   depending on a cancelled or unknown flight becomes unscheduled with a
   clear reason.
2. **Cycles are rejected.** Any flight participating in a dependency cycle is
   marked unscheduled.
3. **Length-incompatible flights are rejected upfront.** If
   `min_runway_length` exceeds the longest configured runway, the flight is
   unscheduled with a "no suitable runway" reason.
4. **Dependency tiers, then priority.** Flights are scheduled in
   topological-tier order. Inside each tier the order is
   `(priority_rank, submission_seq, flight_number)`, so high-priority and
   earlier submissions go first deterministically.
5. **Earliest valid slot wins.** For each flight the scheduler picks the
   earliest start time across all compatible runways that respects:
   - runway separation buffer based on the operation pair,
   - gate availability for the turnaround window (after for arrivals, before
     for departures),
   - ground crew capacity during the runway slot,
   - dependency finish + `ATC_DEPENDENCY_BUFFER_SEC`,
   - the `ATC_MAX_HORIZON_SEC` ceiling.
6. **Deterministic output.** The same inputs and configuration always yield
   the same schedule.

## Running the validation scenarios

```bash
python -m unittest tests.test_scenarios -v
```

Tests cover:

* Scenario 1 — Morning Rush (priority + no overlapping ops).
* Scenario 2 — Heavy Hauler (oversize flight unscheduled with reason).
* Scenario 3 — Connecting Flight (dependency + buffer respected).
* Determinism (same inputs → same schedule).
* Cancellation (dependents re-evaluated).
* Bottleneck (longest chain identified).
* Config validation (missing values fail fast).

## Repository layout

```
task-4/
├── README.md
├── report.md
├── requirements.txt
├── pyproject.toml
├── .env.example
├── atc_mcp/
│   ├── __init__.py
│   ├── __main__.py        # `python -m atc_mcp`
│   ├── config.py          # env parsing + validation
│   ├── models.py          # Pydantic models
│   ├── scheduler.py       # placement, dependencies, bottleneck
│   ├── airport.py         # in-memory state, thread-safe
│   └── server.py          # FastMCP tools + resources
└── tests/
    └── test_scenarios.py
```
