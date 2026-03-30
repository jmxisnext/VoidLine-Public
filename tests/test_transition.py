"""
Tests for the transition 3-on-2 fast break scenario.

Validates VoidLine generalization beyond the PNR fixture:
  - cascading topology (two sequential junctions)
  - non-monotonic pressure shape (rise-and-fall)
  - mid-play constraint activation (CONSTRAINT_ACTIVATED event)
  - wing_kick degradation when recovering defender arrives
  - replay divergence when recovering defender is removed
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.engine.tick import EventKind, TickEngine
from src.rail.graph import load_railgraph
from src.replay import ConstraintChanges, replay_from_tick
from src.replay.report import build_report, render_text


SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"


@pytest.fixture
def transition_graph():
    return load_railgraph(SCENARIOS_DIR / "transition_3on2.json")


@pytest.fixture
def baseline(transition_graph, transition_constraints):
    engine = TickEngine(
        transition_graph, transition_constraints, "SG_02", "primary_read",
        role="ball_handler",
    )
    return engine.run(duration=3.0, dt=0.1)


# ---------------------------------------------------------------------------
# Graph structure
# ---------------------------------------------------------------------------

class TestGraphStructure:
    def test_node_count(self, transition_graph):
        assert len(transition_graph.nodes) == 8

    def test_edge_count(self, transition_graph):
        assert len(transition_graph.edges) == 8

    def test_two_junctions(self, transition_graph):
        junctions = [n for n in transition_graph.nodes.values() if n.node_type == "junction"]
        assert len(junctions) == 2
        assert {j.id for j in junctions} == {"primary_read", "lane_drive"}

    def test_primary_read_corridors(self, transition_graph, transition_constraints):
        viabs = transition_graph.corridor_viabilities(
            "primary_read", transition_constraints, timestamp=0.0, role="ball_handler",
        )
        edge_ids = {v.edge_id for v in viabs}
        assert edge_ids == {"wing_kick", "pull_up", "attack_lane"}

    def test_lane_drive_corridors(self, transition_graph, transition_constraints):
        viabs = transition_graph.corridor_viabilities(
            "lane_drive", transition_constraints, timestamp=0.0, role="ball_handler",
        )
        edge_ids = {v.edge_id for v in viabs}
        assert edge_ids == {"finish", "drop_off", "late_kick"}


# ---------------------------------------------------------------------------
# Non-monotonic pressure shape
# ---------------------------------------------------------------------------

class TestNonMonotonicPressure:
    def test_pressure_drops_then_rises(self, baseline):
        """
        Pressure should decrease as momentum/trail constraints expire,
        then increase when recovering_defender_wing activates at t=1.0.
        Validate the shape, not exact decimals.
        """
        # Sample at key moments
        def pressure_at(t: float) -> float:
            snap = min(baseline, key=lambda s: abs(s.timestamp - t))
            return snap.field.space_pressure

        p_start = pressure_at(0.0)
        p_mid = pressure_at(0.9)   # after momentum + trail expired, before recovery
        p_spike = pressure_at(1.1)  # just after recovering defender arrives

        # Pressure should drop from start to mid
        assert p_mid < p_start, "pressure should drop as early constraints expire"
        # Pressure should rise from mid to spike (non-monotonic)
        assert p_spike > p_mid, "pressure should rise when recovering defender activates"

    def test_pressure_not_monotonically_decreasing(self, baseline):
        """Unlike PNR, pressure should not only decrease over time."""
        pressures = [s.field.space_pressure for s in baseline]
        # Check that at least one tick has higher pressure than the previous
        increases = sum(1 for i in range(1, len(pressures)) if pressures[i] > pressures[i - 1])
        assert increases > 0, "transition pressure should have at least one increase"


# ---------------------------------------------------------------------------
# CONSTRAINT_ACTIVATED event
# ---------------------------------------------------------------------------

class TestConstraintActivation:
    def test_recovering_defender_activated_event(self, baseline):
        """recovering_defender_wing should emit CONSTRAINT_ACTIVATED around t=1.0."""
        activated = [
            (s.timestamp, e)
            for s in baseline
            for e in s.events
            if e.kind == EventKind.CONSTRAINT_ACTIVATED and e.name == "recovering_defender_wing"
        ]
        assert len(activated) == 1
        ts, event = activated[0]
        assert 0.9 <= ts <= 1.1

    def test_multiple_expiry_events(self, baseline):
        """sprint_momentum, trail_runner_not_set, top_defender should all expire."""
        expired_names = {
            e.name
            for s in baseline
            for e in s.events
            if e.kind == EventKind.CONSTRAINT_EXPIRED
        }
        assert "sprint_momentum" in expired_names
        assert "trail_runner_not_set" in expired_names
        assert "top_defender_foul_line" in expired_names


# ---------------------------------------------------------------------------
# wing_kick degradation (headline corridor)
# ---------------------------------------------------------------------------

class TestWingKickDegradation:
    def test_wing_kick_degrades_after_recovery(self, baseline):
        """wing_kick viability should drop after recovering defender arrives at t=1.0."""
        def wing_viability_at(t: float) -> float:
            snap = min(baseline, key=lambda s: abs(s.timestamp - t))
            return next(v.viability for v in snap.viabilities if v.edge_id == "wing_kick")

        v_before = wing_viability_at(0.9)
        v_after = wing_viability_at(1.1)
        assert v_after < v_before, "wing_kick should degrade when recovering defender arrives"

    def test_wing_kick_blocked_by_recovering_defender(self, baseline):
        """After t=1.0, wing_kick should list recovering_defender_wing as a blocker."""
        snap = min(baseline, key=lambda s: abs(s.timestamp - 1.5))
        wing = next(v for v in snap.viabilities if v.edge_id == "wing_kick")
        assert "recovering_defender_wing" in wing.blocked_by


# ---------------------------------------------------------------------------
# Replay: "What if the recovering defender had not arrived?"
# ---------------------------------------------------------------------------

class TestRecoveringDefenderReplay:
    def test_first_divergence_at_activation(self, baseline, transition_graph, transition_constraints):
        """Removing recovering_defender_wing should produce first divergence at t=1.0."""
        changes = ConstraintChanges(remove=["recovering_defender_wing"])
        result = replay_from_tick(
            baseline, transition_graph, transition_constraints,
            fork_tick=0, changes=changes, node_id="primary_read", role="ball_handler",
        )
        assert result.first_divergence_index is not None
        div_ts = result.summary.first_divergence_timestamp
        assert div_ts is not None
        assert 0.9 <= div_ts <= 1.1

    def test_replay_has_less_pressure(self, baseline, transition_graph, transition_constraints):
        """Without recovering defender, late-timeline pressure should be lower."""
        changes = ConstraintChanges(remove=["recovering_defender_wing"])
        result = replay_from_tick(
            baseline, transition_graph, transition_constraints,
            fork_tick=0, changes=changes, node_id="primary_read", role="ball_handler",
        )
        # After t=1.0, replay should show less pressure (constraint removed)
        late_divs = [d for d in result.divergences if d.timestamp >= 1.1]
        for d in late_divs:
            assert d.pressure_delta < 0, "replay should have less pressure without recovering defender"

    def test_wing_kick_stays_viable_in_replay(self, baseline, transition_graph, transition_constraints):
        """wing_kick should remain high viability in replay without the recovering defender."""
        changes = ConstraintChanges(remove=["recovering_defender_wing"])
        result = replay_from_tick(
            baseline, transition_graph, transition_constraints,
            fork_tick=0, changes=changes, node_id="primary_read", role="ball_handler",
        )
        # After t=1.0, wing_kick should be MORE viable in replay
        late_divs = [d for d in result.divergences if d.timestamp >= 1.1]
        for d in late_divs:
            assert d.viability_deltas["wing_kick"] > 0, "wing_kick should be better without recovering defender"

    def test_wing_kick_in_corridors_changed(self, baseline, transition_graph, transition_constraints):
        """Summary should identify wing_kick as the headline changed corridor."""
        changes = ConstraintChanges(remove=["recovering_defender_wing"])
        result = replay_from_tick(
            baseline, transition_graph, transition_constraints,
            fork_tick=0, changes=changes, node_id="primary_read", role="ball_handler",
        )
        assert "wing_kick" in result.summary.corridors_changed

    def test_replay_report_renders(self, baseline, transition_graph, transition_constraints):
        """The replay report should render for the transition scenario."""
        changes = ConstraintChanges(remove=["recovering_defender_wing"])
        result = replay_from_tick(
            baseline, transition_graph, transition_constraints,
            fork_tick=0, changes=changes, node_id="primary_read", role="ball_handler",
        )
        report = build_report(result)
        text = render_text(report)
        assert "recovering_defender_wing" in text
        assert "wing_kick" in text
        assert "VoidLine Replay Report" in text
