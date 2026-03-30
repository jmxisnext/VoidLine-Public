"""
Shared test fixtures for VoidLine.

Provides deterministic seeds, known-good constraint sets,
and reference possibility fields to assert against.
"""

from __future__ import annotations

import pytest

from src.field.space_model import Point, Circle, Cone, TimeWindow, Corridor
from src.constraints.types import (
    Constraint,
    SpatialConstraint,
    TemporalConstraint,
    KinematicConstraint,
    RoleConstraint,
    PerceptualConstraint,
    RiskConstraint,
    ConstraintDynamics,
    ConstraintSource,
    Stability,
)


SEED = 42
AGENT_ID = "PG_01"
TRANSITION_AGENT_ID = "SG_02"


# ---------------------------------------------------------------------------
# Court positions (PNR scenario)
# ---------------------------------------------------------------------------

@pytest.fixture
def top_of_key() -> Point:
    return Point(x=0.0, y=0.0, label="top_of_key")


@pytest.fixture
def left_elbow() -> Point:
    return Point(x=-6.0, y=-8.0, label="left_elbow")


@pytest.fixture
def right_wing() -> Point:
    return Point(x=-6.0, y=12.0, label="right_wing")


@pytest.fixture
def paint_center() -> Point:
    return Point(x=0.0, y=0.0, label="paint_center")


# ---------------------------------------------------------------------------
# Known-good constraint set (PNR at t=0)
# ---------------------------------------------------------------------------

@pytest.fixture
def pnr_constraints() -> list[Constraint]:
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


# ---------------------------------------------------------------------------
# Known-good constraint set (Transition 3-on-2 fast break)
# ---------------------------------------------------------------------------

@pytest.fixture
def transition_constraints() -> list[Constraint]:
    """Seven constraints for the 3-on-2 fast break scenario."""
    return [
        SpatialConstraint(
            name="rim_protector",
            source=ConstraintSource.OPPONENT,
            dynamics=ConstraintDynamics(stability=Stability.STATIC),
            boundary=Circle(center=Point(x=0.0, y=0.0), radius=4.0),
            volume=0.20,
            agent_id=TRANSITION_AGENT_ID,
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
            agent_id=TRANSITION_AGENT_ID,
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
            agent_id=TRANSITION_AGENT_ID,
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
            agent_id=TRANSITION_AGENT_ID,
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
            agent_id=TRANSITION_AGENT_ID,
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
            agent_id=TRANSITION_AGENT_ID,
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
            agent_id=TRANSITION_AGENT_ID,
            awareness_delay=0.5,
        ),
    ]
