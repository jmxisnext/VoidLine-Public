# VoidLine

**Possibility Field Engine**

A constraint-driven negative-space engine that models how live pressure removes available possibility from a continuous spatial field, evolves that pressure over time, and supports counterfactual replay to prove what would have changed if a single constraint were different.

---

## Core Thesis

The product is **surviving possibility**, not chosen action.

Most simulation systems model what agents *do*. VoidLine models what agents *could still do* — and what removed the rest. The action is only the visible consequence. The real object is the shape of remaining possibility and the constraints that carved it.

**Three layers:**

1. **Raw court space** — continuous spatial field in ISO4D-aligned coordinates (feet from basket center)
2. **Negative-space transform** — six constraint categories carve away possibility
3. **Action selection over survivors** — scoring happens only over what survived

---

## What It Computes

At any moment, VoidLine answers:

- How much usable possibility remains?
- Where is it located?
- What removed the rest, and why?
- How does that change when a constraint expires or appears?
- What would have been different if one constraint had not changed?

---

## Constraint Categories

Every constraint is a function that removes a region of possibility from the action space:

| Category | What it removes | Example |
|---|---|---|
| **Spatial** | Physical court regions | Defender denial area, blocked lane |
| **Temporal** | Time windows | Shot clock pressure, help defender arriving |
| **Kinematic** | Movement corridors | Overcommitted momentum, fatigue |
| **Role** | Actions invalid for current role | Not the ball handler, screener must hold |
| **Perceptual** | Actions requiring unseen information | Target behind vision cone |
| **Risk** | Actions exceeding risk thresholds | Contested shot above turnover limit |

The possibility field is what survives their union.

---

## Validated Scenarios

Two scenarios validate that VoidLine generalizes across topology, temporal profile, and dominant constraint direction.

| | **PNR (Pick-and-Roll)** | **Transition (3-on-2 Fast Break)** |
|---|---|---|
| **Topology** | Star — 1 junction, 5 spokes | Cascading — 2 sequential junctions |
| **Temporal shape** | Monotonic pressure decrease | Non-monotonic rise-and-fall |
| **Key event** | Constraints expire, space reopens | Constraint activates mid-play, space closes |
| **Headline corridor** | `drive_left` | `wing_kick` |
| **Replay question** | "What if the help defender hadn't rotated?" | "What if the recovering defender hadn't arrived?" |
| **Replay result** | Pressure stays higher, drive stays degraded | Pressure stays lower, wing kick stays viable |

### PNR: Expiry-Driven Reopening

Seven constraints active at t=0.0. At t=1.2, three expire simultaneously (help defender rotates out, screen arrives, momentum decays). Pressure drops from 90% to 45%. `drive_left` recovers from 86% to 97% viability.

```
t=0.0s  drive_left viability=86%   blocked by: help_defender_paint
t=1.2s  drive_left viability=97%   (help defender expired)
```

**Counterfactual:** Replace `help_defender_paint` with a sustained version that never expires. Replay shows pressure stays 20+ points higher and `drive_left` remains degraded. First divergence at t=1.2.

### Transition: Activation-Driven Closure

Seven constraints including a recovering defender that **activates at t=1.0** (not present at start). Pressure drops as sprint momentum and trail-runner constraints expire, then **rises** when the recovering defender arrives and closes the wing passing lane.

**Counterfactual:** Remove `recovering_defender_wing` entirely. Replay shows pressure stays low and `wing_kick` remains fully viable. First divergence at t=1.0 — the inverse pattern from PNR.

---

## Architecture

```
Core (the product):
    field/          spatial primitives, continuous court model
    constraints/    six carving categories with temporal dynamics
    envelope/       possibility field computation, removal attribution, diff

Consumer (downstream of core):
    rail/           authored topology, corridor viability projection
    engine/         tick loop — time-evolving constraint fields, event detection
    replay/         single-fork counterfactual with aligned divergence analysis
    agents/         archetypes score over surviving space (planned)
    memory/         envelope-keyed tabular memory (planned)
```

---

## Milestones

| Tag | What it contains |
|---|---|
| **v0.1.0-foundation** | Field, constraints, envelope, rail viability, PNR scenario |
| **v0.2.0-temporal-replay** | Tick engine, event detection, replay, aligned divergence analysis |
| **v0.2.1-replay-report** | Plain-text replay report artifact for counterfactual demos |
| **v0.3.0-transition** | Second scenario (3-on-2 fast break), proves generalization across topology and temporal profile |

---

## Implemented

- `Point`, `Circle`, `Cone`, `Corridor`, `TimeWindow` — spatial primitives (ISO4D-aligned)
- Six constraint types with temporal dynamics (static, sustained, transient, decaying)
- `PossibilityField` — surviving volume, space pressure, collapse detection, removal attribution by source
- `FieldDiff` — counterfactual comparison via removed/reopened space
- `RailGraph` — JSON-schema-validated topology loader with node types and role filtering
- `CorridorViability` — sampling-based projection of negative space onto corridor geometry with per-constraint blocker attribution
- `TickEngine` — advances time in discrete steps, recomputes field and viabilities each tick, emits events when constraints expire/activate or corridors open/collapse
- `replay_from_tick()` — forks a baseline timeline at one tick, applies constraint changes with deterministic precedence, reruns at exact baseline timestamps, compares aligned timelines at field/corridor/event level
- `ConstraintChanges` — remove/add/replace with explicit precedence rules and collision detection
- `ReplayResult` — per-tick divergence records, first divergence index and timestamp, aggregate summary with max corridor deltas
- `ReplayReport` — structured report with text rendering: fork timestamp, first divergence, pressure/volume deltas, changed corridors, event attribution, natural-language conclusion
- PNR scenario (`scenarios/pnr_basic.json`) — 7 nodes, 7 edges, star topology from screen point
- Transition scenario (`scenarios/transition_3on2.json`) — 8 nodes, 8 edges, cascading topology with two sequential junctions
- 105 tests passing across both scenarios

---

## Known Limitations

- **Naive pressure aggregation.** Constraint volumes are summed, not geometrically unioned. Two overlapping constraints double-count their removed volume. Reported pressure values are clamped but may overstate true removal in dense constraint configurations. The shape of pressure over time is reliable; exact decimals are not.
- **Sampling-based corridor viability.** Corridor viability is computed by sampling points along the corridor centerline and testing each against constraint boundaries. This is correct and debuggable but resolution-dependent. Fine-grained spatial effects near constraint boundaries may differ with different sample spacing.
- **Single-agent per scenario.** Each scenario tracks one agent's possibility field. Multi-agent interaction (e.g., how one agent's constraint field affects another's) is not modeled.
- **Static constraint geometry.** Constraint boundaries do not move over time — they activate and expire but do not translate. Moving defenders are modeled as sequential transient constraints, not as continuously repositioning boundaries.
- **Two scenarios validated.** The engine has been tested against PNR and transition topologies. Other play types (post-up, closeout, zone offense) have not been validated.

---

## Running

```bash
python -m venv .venv
source .venv/bin/activate    # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
pytest -v
```

Run the help-defender replay demo:

```bash
python -m examples.help_defender_replay
```

Requires Python 3.11+.

---

## Coordinate System

Matches [ISO4D](https://github.com/jmxisnext) convention:

| Property | Value |
|---|---|
| Origin | Center of attacking hoop (basket) |
| Units | Feet |
| +X | Toward baseline (behind hoop) |
| -X | Toward mid-court |
| +Y | Right wing |
| -Y | Left wing |

---

## Design Principles

- **Negative space is the product.** Rails give structure. Constraints carve space. Decisions are evidence.
- **Constraints compose via union.** Adding constraints reduces possibility — it doesn't increase computational complexity.
- **Attribution over aggregation.** Every removal is named, sourced, and measured.
- **Deterministic and inspectable.** Same inputs, same field. Every corridor viability can be traced to specific constraint boundaries.
- **Replay proves causation.** Aligned divergence analysis shows exactly where and why two timelines split.
