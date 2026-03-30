#!/usr/bin/env python3
"""
VoidLine Demo: What if the help defender had not rotated?

Runs the PNR scenario baseline, forks at t=0, replaces
help_defender_paint with a sustained version that never expires,
and prints the replay report.

Usage:
    python -m examples.help_defender_replay
"""

import sys
from pathlib import Path

# Ensure repo root is on sys.path when run directly
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.field.space_model import Point, Circle, Cone, TimeWindow
from src.constraints.types import (
    ConstraintDynamics,
    ConstraintSource,
    KinematicConstraint,
    PerceptualConstraint,
    RiskConstraint,
    RoleConstraint,
    SpatialConstraint,
    Stability,
    TemporalConstraint,
)
from src.engine.tick import TickEngine
from src.rail.graph import load_railgraph
from src.replay import ConstraintChanges, replay_from_tick
from src.replay.report import build_report, render_text


AGENT_ID = "PG_01"
SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"


def pnr_constraints():
    """Seven constraints from the PNR scenario at t=0.0."""
    return [
        SpatialConstraint(
            name="onball_defender_left_shade",
            source=ConstraintSource.OPPONENT,
            dynamics=ConstraintDynamics(stability=Stability.SUSTAINED),
            boundary=Circle(center=Point(x=-1.5, y=-6.0), radius=2.0),
            volume=0.25,
            agent_id=AGENT_ID,
        ),
        SpatialConstraint(
            name="help_defender_paint",
            source=ConstraintSource.OPPONENT,
            dynamics=ConstraintDynamics(
                stability=Stability.TRANSIENT,
                active_window=TimeWindow(start=0.0, end=1.2),
            ),
            boundary=Circle(center=Point(x=0.0, y=1.5), radius=2.5),
            volume=0.20,
            agent_id=AGENT_ID,
        ),
        TemporalConstraint(
            name="shot_clock_14s",
            source=ConstraintSource.RULES,
            dynamics=ConstraintDynamics(
                stability=Stability.DECAYING,
                decay_half_life=7.0,
            ),
            boundary=TimeWindow(start=0.0, end=14.0),
            volume=0.05,
            agent_id=AGENT_ID,
            deadline=14.0,
        ),
        KinematicConstraint(
            name="rightward_momentum",
            source=ConstraintSource.SELF,
            dynamics=ConstraintDynamics(
                stability=Stability.TRANSIENT,
                active_window=TimeWindow(start=0.0, end=0.4),
            ),
            boundary=None,
            volume=0.15,
            agent_id=AGENT_ID,
            commitment_direction=Point(x=1.0, y=-0.3),
            recovery_time=0.4,
        ),
        RoleConstraint(
            name="screen_not_yet_set",
            source=ConstraintSource.RULES,
            dynamics=ConstraintDynamics(
                stability=Stability.TRANSIENT,
                active_window=TimeWindow(start=0.0, end=0.8),
            ),
            boundary=None,
            volume=0.10,
            agent_id=AGENT_ID,
            required_role="pnr_ball_handler",
            current_role="iso_ball_handler",
        ),
        PerceptualConstraint(
            name="weak_side_blind_spot",
            source=ConstraintSource.PERCEPTION,
            dynamics=ConstraintDynamics(stability=Stability.SUSTAINED),
            boundary=Cone(
                origin=Point(x=0.0, y=0.0),
                direction_deg=0.0,
                half_angle_deg=60.0,
            ),
            volume=0.08,
            agent_id=AGENT_ID,
            awareness_delay=0.6,
        ),
        RiskConstraint(
            name="contested_pullup",
            source=ConstraintSource.RISK,
            dynamics=ConstraintDynamics(stability=Stability.SUSTAINED),
            boundary=None,
            volume=0.07,
            agent_id=AGENT_ID,
            risk_value=0.55,
            threshold=0.40,
            risk_type="contested_shot",
        ),
    ]


def main():
    # Load topology
    graph = load_railgraph(SCENARIOS_DIR / "pnr_basic.json")
    constraints = pnr_constraints()

    # Run baseline
    engine = TickEngine(
        graph, constraints, AGENT_ID, "screen_point", role="ball_handler",
    )
    baseline = engine.run(duration=2.0, dt=0.1)

    # Fork: help defender persists (never rotates out)
    help_original = next(c for c in constraints if c.name == "help_defender_paint")
    help_persistent = SpatialConstraint(
        name="help_defender_paint",
        source=help_original.source,
        dynamics=ConstraintDynamics(stability=Stability.SUSTAINED),
        boundary=help_original.boundary,
        volume=help_original.volume,
        agent_id=help_original.agent_id,
    )
    changes = ConstraintChanges(replace={"help_defender_paint": help_persistent})

    # Replay
    result = replay_from_tick(
        baseline, graph, constraints,
        fork_tick=0, changes=changes,
        node_id="screen_point", role="ball_handler",
    )

    # Report
    report = build_report(result)
    print(render_text(report))


if __name__ == "__main__":
    main()
