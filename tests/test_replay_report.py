"""
Tests for the replay report artifact.

Validates structured report fields and text rendering
against the help-defender demo case.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.field.space_model import Point, Circle
from src.constraints.types import (
    SpatialConstraint,
    ConstraintDynamics,
    ConstraintSource,
    Stability,
)
from src.engine.tick import TickEngine
from src.rail.graph import load_railgraph
from src.replay import ConstraintChanges, replay_from_tick
from src.replay.report import ReplayReport, build_report, render_text


SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"


@pytest.fixture
def pnr_graph():
    return load_railgraph(SCENARIOS_DIR / "pnr_basic.json")


@pytest.fixture
def baseline(pnr_graph, pnr_constraints):
    engine = TickEngine(
        pnr_graph, pnr_constraints, "PG_01", "screen_point", role="ball_handler",
    )
    return engine.run(duration=2.0, dt=0.1)


@pytest.fixture
def help_defender_result(baseline, pnr_graph, pnr_constraints):
    """The flagship demo: what if help defender had not rotated?"""
    help_original = next(c for c in pnr_constraints if c.name == "help_defender_paint")
    help_persistent = SpatialConstraint(
        name="help_defender_paint",
        source=help_original.source,
        dynamics=ConstraintDynamics(stability=Stability.SUSTAINED),
        boundary=help_original.boundary,
        volume=help_original.volume,
        agent_id=help_original.agent_id,
    )
    changes = ConstraintChanges(replace={"help_defender_paint": help_persistent})
    return replay_from_tick(
        baseline, pnr_graph, pnr_constraints,
        fork_tick=0, changes=changes, node_id="screen_point", role="ball_handler",
    )


# ---------------------------------------------------------------------------
# Structured report
# ---------------------------------------------------------------------------

class TestBuildReport:
    def test_returns_replay_report(self, help_defender_result):
        report = build_report(help_defender_result)
        assert isinstance(report, ReplayReport)

    def test_fork_timestamp(self, help_defender_result):
        report = build_report(help_defender_result)
        assert report.fork_timestamp == 0.0

    def test_first_divergence_timestamp(self, help_defender_result):
        report = build_report(help_defender_result)
        assert report.first_divergence_timestamp is not None
        assert 1.1 <= report.first_divergence_timestamp <= 1.3

    def test_divergent_ticks(self, help_defender_result):
        report = build_report(help_defender_result)
        assert report.divergent_ticks > 0
        assert report.divergent_ticks <= report.total_ticks

    def test_pressure_delta_positive(self, help_defender_result):
        """Replay has more pressure (help persists)."""
        report = build_report(help_defender_result)
        assert report.max_pressure_delta > 0.01

    def test_corridors_changed_includes_drive_left(self, help_defender_result):
        report = build_report(help_defender_result)
        assert "drive_left" in report.corridors_changed

    def test_constraints_replaced(self, help_defender_result):
        report = build_report(help_defender_result)
        assert "help_defender_paint" in report.constraints_replaced

    def test_baseline_only_events_show_expiry(self, help_defender_result):
        report = build_report(help_defender_result)
        assert "help_defender_paint" in report.baseline_only_events.constraint_expired

    def test_conclusion_is_nonempty(self, help_defender_result):
        report = build_report(help_defender_result)
        assert len(report.conclusion) > 0
        assert "help_defender_paint" in report.conclusion


# ---------------------------------------------------------------------------
# Text rendering
# ---------------------------------------------------------------------------

class TestRenderText:
    def test_contains_header(self, help_defender_result):
        report = build_report(help_defender_result)
        text = render_text(report)
        assert "VoidLine Replay Report" in text

    def test_contains_fork_timestamp(self, help_defender_result):
        report = build_report(help_defender_result)
        text = render_text(report)
        assert "fork at:" in text

    def test_contains_divergence_info(self, help_defender_result):
        report = build_report(help_defender_result)
        text = render_text(report)
        assert "first divergence:" in text
        assert "divergent ticks:" in text

    def test_contains_constraint_change(self, help_defender_result):
        report = build_report(help_defender_result)
        text = render_text(report)
        assert "replaced: help_defender_paint" in text

    def test_contains_corridor(self, help_defender_result):
        report = build_report(help_defender_result)
        text = render_text(report)
        assert "drive_left" in text

    def test_contains_conclusion(self, help_defender_result):
        report = build_report(help_defender_result)
        text = render_text(report)
        assert "Conclusion:" in text


# ---------------------------------------------------------------------------
# No-change report
# ---------------------------------------------------------------------------

class TestNoChangeReport:
    def test_no_change_no_divergence(self, baseline, pnr_graph, pnr_constraints):
        result = replay_from_tick(
            baseline, pnr_graph, pnr_constraints,
            fork_tick=0, changes=ConstraintChanges(),
            node_id="screen_point", role="ball_handler",
        )
        report = build_report(result)
        assert report.first_divergence_timestamp is None
        assert report.divergent_ticks == 0
        assert "No divergence" in report.conclusion

    def test_no_change_text_renders(self, baseline, pnr_graph, pnr_constraints):
        result = replay_from_tick(
            baseline, pnr_graph, pnr_constraints,
            fork_tick=0, changes=ConstraintChanges(),
            node_id="screen_point", role="ball_handler",
        )
        report = build_report(result)
        text = render_text(report)
        assert "first divergence:  (none)" in text
