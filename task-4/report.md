# Task 4 — Report

## Approach

The brief frames the MCP server as an AI-readable Air Traffic Control system,
so I built it around three concerns kept in separate files:

1. **Config** (`config.py`) — strict environment parsing with a `ConfigError`
   that fails the process at startup if anything is missing or malformed.
   Runways are typed `(id, length)` tuples so the scheduler can reason about
   capability, not just count.
2. **Scheduler** (`scheduler.py`) — a pure function that takes a list of
   flights plus the config and returns a schedule. Pure means the same inputs
   always yield the same outputs, which made determinism a property of the
   design rather than something to bolt on afterwards.
3. **Airport state + MCP wrapper** (`airport.py`, `server.py`) — the only
   stateful pieces. The airport owns the in-memory store and a lock so MCP
   tool calls are safe to run concurrently. The MCP wrapper is a thin shell
   around it.

I chose **FastMCP** from the official Python SDK so tools and resources stay
declarative. Each tool is a regular Python function with a docstring; the SDK
exposes the signature to the AI client as a typed schema.

## Scheduling algorithm

The scheduler is a deterministic greedy placer with three passes:

1. **Validate**: cycle detection (DFS with grey/black colouring), missing
   dependencies, and impossibility checks (e.g. `min_runway_length` exceeds
   the longest runway). Anything failing here is marked unscheduled with a
   human-readable reason.
2. **Tier**: Kahn's algorithm produces dependency tiers so the placer never
   has to revisit a flight to fix dependency order. Inside each tier flights
   are sorted by `(priority_rank, submission_seq, flight_number)` — the
   flight number is the deterministic tie-breaker.
3. **Place**: for each flight, walk runways from shortest-compatible to
   longest, find the earliest start that respects separation buffers,
   dependency finish + buffer, gate turnaround occupation, and ground crew
   capacity. Across runways we keep the candidate with the earliest finish
   time. If nothing fits inside `ATC_MAX_HORIZON_SEC`, the flight is
   unscheduled.

Gates are modeled as a window adjacent to the runway slot — after the runway
op for arrivals, before it for departures. Ground crew is a counted resource
overlapping the runway slot. These three constraints together give us a
realistic enough conflict surface to exercise without becoming a full sim.

## Bottleneck analysis

The "longest dependency chain" capability is a memoised DFS over the
scheduled DAG. Each node's value is `op_duration + max(child_chain) +
dep_buffer`. Tie-breaks use lexicographic ordering of chain ids so identical
inputs produce identical chain output. The result returns both the ordered
flight numbers and the total elapsed wall-clock seconds.

## What worked

- **Pure scheduler + thin state wrapper.** Made it trivial to write the
  validation scenarios as unit tests without spinning up the MCP transport.
- **Pydantic models for inputs.** The `submit_flight` tool gets typed
  validation for free, including normalised flight numbers (upper-cased,
  trimmed) and de-duplicated dependency lists.
- **Tier-based scheduling** dodged the classic mistake of re-running the
  placer when a dependency moves. Because we know every dependency is placed
  before the dependent is touched, we just consult its `finish_sec`.
- **Deterministic tie-breakers everywhere.** Sorting by
  `(priority, submission_seq, flight_number)` and `(start_sec, runway, id)`
  for timeline output makes the test suite painless and the AI client's view
  stable across re-reads.

## What did not work / open trade-offs

- **No interval tree.** For airports with thousands of flights, scanning the
  runway booking list per candidate is O(n²). For the size the brief implies
  (dozens to a few hundred flights) it is fine. Adding a sorted-interval
  structure is the next obvious upgrade.
- **No preemption.** A high-priority flight that arrives after a low-priority
  one is queued does not bump it out of its slot — it only gets ordered
  earlier inside its dependency tier on the next `generate_schedule`. That
  matches the brief ("scheduled earlier where possible") but is worth
  flagging.
- **Single airport instance per process.** State is in-memory. A real
  deployment would back this with a persistent store; I deliberately
  punted on that to keep the surface area small.
- **MCP `notifications/resources/list_changed`** is not emitted. Resources
  refresh on read, which is sufficient for the assignment, but a real client
  would benefit from change notifications after `submit_flight` /
  `generate_schedule`.

## Tools and techniques used

- **Python 3.10+** with **Pydantic v2** for input validation and output
  serialization.
- The **official `mcp` Python SDK** (`FastMCP`) for tool/resource
  registration over stdio.
- **`unittest`** for the validation scenarios — no extra dependency,
  easy to run with `python -m unittest`.
- **AI-pairing**: I drafted the scheduler iteratively with Claude (this
  session). The mental model — tier first, then greedy placement with
  earliest-finish selection — came from a short whiteboard session before
  any code was written. The model wrote the scaffold, I tightened the slot
  search and the bottleneck DP myself.
- **No corporate data** was provided to any AI tool at any point.

## Notable decisions

- **`min_runway_length` is the only runway requirement.** The brief mentions
  "runway requirements" generally; modelling length covers the realistic
  case (heavies need long runways) without over-specifying.
- **Cancellation invalidates the schedule.** Rather than try to patch the
  existing schedule in place, `cancel_flight` flips the schedule state to
  "stale" and the next `generate_schedule` recomputes from scratch. The
  brief's "calling this tool replaces the current schedule with a freshly
  computed one" language pushed me towards this clean re-compute model.
- **Unscheduled flights remain visible.** They keep their submission record
  and a `reason` field. This is the single most useful debugging signal for
  an AI client trying to understand why an operation was not placed.
