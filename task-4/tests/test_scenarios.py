"""End-to-end validation scenarios from the brief.

Run with: ``python -m unittest tests.test_scenarios``
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from atc_mcp.airport import Airport
from atc_mcp.config import AirportConfig, RunwaySpec, load_config
from atc_mcp.models import FlightSubmission


def make_config(**overrides) -> AirportConfig:
    base = dict(
        runways=(
            RunwaySpec("R1", 3000),
            RunwaySpec("R2", 4000),
        ),
        gates=("G1", "G2"),
        ground_crew=4,
        runway_buffer_takeoff_sec=120,
        runway_buffer_landing_sec=90,
        runway_buffer_mixed_sec=180,
        arrival_duration_sec=300,
        departure_duration_sec=300,
        gate_turnaround_sec=1800,
        dependency_buffer_sec=600,
        max_horizon_sec=86400,
        epoch=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    base.update(overrides)
    return AirportConfig(**base)


def submit(airport: Airport, **kwargs) -> None:
    airport.submit(FlightSubmission(**kwargs))


class MorningRushScenario(unittest.TestCase):
    """Scenario 1: mixed arrivals/departures, priority influences ordering."""

    def setUp(self) -> None:
        self.cfg = make_config(
            runways=(RunwaySpec("R1", 3000),),  # one runway forces contention
            gates=("G1", "G2"),
            ground_crew=2,
        )
        self.airport = Airport(self.cfg)

    def test_all_scheduled_and_priority_respected(self) -> None:
        submit(self.airport, flight_number="FA100", operation="arrival", priority="high")
        submit(self.airport, flight_number="FD200", operation="departure", priority="medium")
        submit(self.airport, flight_number="FA300", operation="arrival", priority="low")
        submit(self.airport, flight_number="FD400", operation="departure", priority="low")

        result = self.airport.generate_schedule()

        # All four flights placed
        self.assertEqual(len(result.scheduled), 4)
        self.assertEqual(len(result.unscheduled), 0)

        # No overlapping ops on the single runway (separation enforced)
        timeline = sorted(result.scheduled, key=lambda e: e.start_sec)
        for prev, nxt in zip(timeline, timeline[1:]):
            self.assertLessEqual(prev.end_sec, nxt.start_sec)

        # High-priority arrival should not be later than the low-priority ones.
        starts = {e.flight_number: e.start_sec for e in result.scheduled}
        self.assertLessEqual(starts["FA100"], starts["FA300"])
        self.assertLessEqual(starts["FA100"], starts["FD400"])


class HeavyHaulerScenario(unittest.TestCase):
    """Scenario 2: a flight whose runway requirement exceeds capability."""

    def setUp(self) -> None:
        self.cfg = make_config(
            runways=(RunwaySpec("R1", 3000), RunwaySpec("R2", 2500)),
        )
        self.airport = Airport(self.cfg)

    def test_oversized_flight_is_unscheduled(self) -> None:
        submit(
            self.airport,
            flight_number="HVY1",
            operation="departure",
            priority="high",
            min_runway_length=5000,
        )
        submit(self.airport, flight_number="REG1", operation="arrival", priority="low")
        result = self.airport.generate_schedule()
        self.assertEqual(len(result.scheduled), 1)
        self.assertEqual(result.scheduled[0].flight_number, "REG1")
        self.assertEqual(len(result.unscheduled), 1)
        u = result.unscheduled[0]
        self.assertEqual(u["flight_number"], "HVY1")
        self.assertIn("runway", u["reason"].lower())


class ConnectingFlightScenario(unittest.TestCase):
    """Scenario 3: outbound depends on inbound completion."""

    def setUp(self) -> None:
        self.cfg = make_config(
            arrival_duration_sec=600,
            departure_duration_sec=600,
            gate_turnaround_sec=1800,
            dependency_buffer_sec=600,
        )
        self.airport = Airport(self.cfg)

    def test_dependency_order_and_buffer(self) -> None:
        submit(self.airport, flight_number="IN1", operation="arrival", priority="medium")
        submit(
            self.airport,
            flight_number="OUT1",
            operation="departure",
            priority="medium",
            dependencies=["IN1"],
        )
        result = self.airport.generate_schedule()
        self.assertEqual(len(result.scheduled), 2)
        timeline = {e.flight_number: e for e in result.scheduled}
        inbound = timeline["IN1"]
        outbound = timeline["OUT1"]
        # outbound must start after inbound finish + dependency buffer
        self.assertGreaterEqual(
            outbound.start_sec, inbound.finish_sec + self.cfg.dependency_buffer_sec
        )


class DeterminismScenario(unittest.TestCase):
    """Identical inputs produce identical schedules."""

    def test_repeatable(self) -> None:
        def run() -> list[tuple[str, int, str]]:
            cfg = make_config()
            airport = Airport(cfg)
            submit(airport, flight_number="A1", operation="arrival", priority="medium")
            submit(airport, flight_number="A2", operation="arrival", priority="high")
            submit(airport, flight_number="D1", operation="departure", priority="low", dependencies=["A1"])
            submit(airport, flight_number="D2", operation="departure", priority="medium")
            result = airport.generate_schedule()
            return [(e.flight_number, e.start_sec, e.runway) for e in result.scheduled]

        self.assertEqual(run(), run())


class CancellationScenario(unittest.TestCase):
    """Cancelling a flight frees its slot and re-evaluates dependents."""

    def test_cancel_releases_resources(self) -> None:
        cfg = make_config()
        airport = Airport(cfg)
        submit(airport, flight_number="A1", operation="arrival", priority="high")
        submit(airport, flight_number="A2", operation="arrival", priority="medium")
        submit(airport, flight_number="D1", operation="departure", priority="medium", dependencies=["A1"])

        first = airport.generate_schedule()
        original_d1 = next(e for e in first.scheduled if e.flight_number == "D1")

        airport.cancel("A1")
        second = airport.generate_schedule()

        # D1 must now be unscheduled (its dependency is gone)
        d1_unscheduled = any(u["flight_number"] == "D1" for u in second.unscheduled)
        self.assertTrue(d1_unscheduled)

        # A2 should still be scheduled
        a2_scheduled = any(e.flight_number == "A2" for e in second.scheduled)
        self.assertTrue(a2_scheduled)
        # Sanity check that we actually had a different state before cancellation
        self.assertIsNotNone(original_d1)


class BottleneckScenario(unittest.TestCase):
    """The longest dependency chain is correctly identified."""

    def test_longest_chain(self) -> None:
        cfg = make_config(dependency_buffer_sec=300)
        airport = Airport(cfg)
        submit(airport, flight_number="L1", operation="arrival", priority="medium")
        submit(airport, flight_number="L2", operation="departure", priority="medium", dependencies=["L1"])
        submit(airport, flight_number="L3", operation="arrival", priority="medium", dependencies=["L2"])
        submit(airport, flight_number="SHORT", operation="arrival", priority="medium")
        airport.generate_schedule()
        result = airport.bottleneck()
        self.assertEqual(result["chain"], ["L1", "L2", "L3"])
        self.assertGreater(result["total_duration_sec"], 0)


class ConfigValidationScenario(unittest.TestCase):
    """Invalid environment configuration fails fast with a clear message."""

    def test_missing_runways(self) -> None:
        from atc_mcp.config import ConfigError

        env = {
            # ATC_RUNWAYS missing
            "ATC_GATES": "2",
            "ATC_GROUND_CREW": "2",
            "ATC_RUNWAY_BUFFER_TAKEOFF_SEC": "60",
            "ATC_RUNWAY_BUFFER_LANDING_SEC": "60",
            "ATC_RUNWAY_BUFFER_MIXED_SEC": "120",
            "ATC_ARRIVAL_DURATION_SEC": "300",
            "ATC_DEPARTURE_DURATION_SEC": "300",
            "ATC_GATE_TURNAROUND_SEC": "1800",
            "ATC_DEPENDENCY_BUFFER_SEC": "600",
            "ATC_MAX_HORIZON_SEC": "86400",
        }
        with self.assertRaises(ConfigError):
            load_config(env)

    def test_full_env_parses(self) -> None:
        env = {
            "ATC_RUNWAYS": "R1:3500,R2:4200",
            "ATC_GATES": "G1,G2,G3",
            "ATC_GROUND_CREW": "5",
            "ATC_RUNWAY_BUFFER_TAKEOFF_SEC": "120",
            "ATC_RUNWAY_BUFFER_LANDING_SEC": "90",
            "ATC_RUNWAY_BUFFER_MIXED_SEC": "180",
            "ATC_ARRIVAL_DURATION_SEC": "300",
            "ATC_DEPARTURE_DURATION_SEC": "300",
            "ATC_GATE_TURNAROUND_SEC": "1800",
            "ATC_DEPENDENCY_BUFFER_SEC": "600",
            "ATC_MAX_HORIZON_SEC": "86400",
            "ATC_EPOCH_ISO": "2026-05-24T00:00:00Z",
        }
        cfg = load_config(env)
        self.assertEqual(len(cfg.runways), 2)
        self.assertEqual(cfg.gates, ("G1", "G2", "G3"))
        self.assertEqual(cfg.epoch.year, 2026)


if __name__ == "__main__":
    unittest.main()
