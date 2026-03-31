#!/usr/bin/env python3
"""
VoidLine Demo: What if the recovering defender had not arrived?

Runs the 3-on-2 transition scenario baseline, forks at t=0,
removes recovering_defender_wing, and prints the replay report.

Usage:
    python -m examples.transition_replay
"""

import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.field.space_model import Point, Circle, Cone, TimeWindow
from src.constraints.types import (
    ConstraintDynamics,
    ConstraintSource,
    KinematicConstraint,
    PerceptualConstraint,
    RoleConstraint,
    SpatialConstraint,
    Stability,
    TemporalConstraint,
)
from src.engine.tick import TickEngine
from src.rail.graph import load_railgraph
from src.replay import ConstraintChanges, replay_from_tick
from src.replay.report import build_report, render_text


AGENT_ID = "SG_02"
SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"


def transition_constraints():
    """Seven constraints for the 3-on-2 fast break scenario."""
    return [
        SpatialConstraint(
            name="rim_protector",
            source=ConstraintSource.OPPONENT,
            dynamics=ConstraintDynamics(stability=Stability.STATIC),
            boundary=Circle(center=Point(x=0.0, y=0.0), radius=4.0),
            volume=0.20,
            agent_id=AGENT_ID,
        ),
        SpatialConstraint(
            name="top_defender_foul_line",
            source=ConstraintSource.OPPONENT,
            dynamics=ConstraintDynamics(
                stability=Stability.TRANSIENT,
                active_window=TimeWindow(start=0.0, end=1.5),
            ),
            boundary=Circle(center=Point(x=-14.0, y=1.0), radius=2.5),
            volume=0.15,
            agent_id=AGENT_ID,
        ),
        SpatialConstraint(
            name="recovering_defender_wing",
            source=ConstraintSource.OPPONENT,
            dynamics=ConstraintDynamics(
                stability=Stability.TRANSIENT,
                active_window=TimeWindow(start=1.0, end=10.0),
            ),
            boundary=Circle(center=Point(x=-18.0, y=-13.0), radius=3.5),
            volume=0.20,
            agent_id=AGENT_ID,
        ),
        KinematicConstraint(
            name="sprint_momentum",
            source=ConstraintSource.SELF,
            dynamics=ConstraintDynamics(
                stability=Stability.TRANSIENT,
                active_window=TimeWindow(start=0.0, end=0.6),
            ),
            boundary=None,
            volume=0.15,
            agent_id=AGENT_ID,
            commitment_direction=Point(x=1.0, y=0.0),
            recovery_time=0.6,
        ),
        TemporalConstraint(
            name="numbers_window",
            source=ConstraintSource.RULES,
            dynamics=ConstraintDynamics(
                stability=Stability.DECAYING,
                decay_half_life=1.25,
            ),
            boundary=TimeWindow(start=0.0, end=2.5),
            volume=0.05,
            agent_id=AGENT_ID,
            deadline=2.5,
        ),
        RoleConstraint(
            name="trail_runner_not_set",
            source=ConstraintSource.SELF,
            dynamics=ConstraintDynamics(
                stability=Stability.TRANSIENT,
                active_window=TimeWindow(start=0.0, end=0.8),
            ),
            boundary=None,
            volume=0.10,
            agent_id=AGENT_ID,
            required_role="trail_man",
            current_role="sprinting",
        ),
        PerceptualConstraint(
            name="blind_backside",
            source=ConstraintSource.PERCEPTION,
            dynamics=ConstraintDynamics(stability=Stability.SUSTAINED),
            boundary=Cone(
                origin=Point(x=-22.0, y=2.0),
                direction_deg=180.0,
                half_angle_deg=60.0,
            ),
            volume=0.08,
            agent_id=AGENT_ID,
            awareness_delay=0.5,
        ),
    ]


def main():
    graph = load_railgraph(SCENARIOS_DIR / "transition_3on2.json")
    constraints = transition_constraints()

    engine = TickEngine(
        graph, constraints, AGENT_ID, "primary_read", role="ball_handler",
    )
    baseline = engine.run(duration=3.0, dt=0.1)

    # Fork: recovering defender never arrives
    changes = ConstraintChanges(remove=["recovering_defender_wing"])

    result = replay_from_tick(
        baseline, graph, constraints,
        fork_tick=0, changes=changes,
        node_id="primary_read", role="ball_handler",
    )

    report = build_report(result)
    print(render_text(report))


if __name__ == "__main__":
    main()
