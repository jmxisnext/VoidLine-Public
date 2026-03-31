"""
replay.report
=============
Structured replay report for demo and inspection.

Consumes a ReplayResult and produces either a structured dict
or a human-readable text summary. No visualization, no HTML —
just the facts needed to explain what diverged and why.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.engine.tick import EventKind
from src.replay.models import ReplayResult, TickDivergence


# ---------------------------------------------------------------------------
# Structured report
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EventSummary:
    """Compact summary of events unique to one timeline."""

    constraint_expired: list[str] = field(default_factory=list)
    constraint_activated: list[str] = field(default_factory=list)
    corridor_opened: list[str] = field(default_factory=list)
    corridor_collapsed: list[str] = field(default_factory=list)
    field_collapsed: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReplayReport:
    """Structured replay report — everything needed to explain divergence."""

    fork_timestamp: float
    first_divergence_timestamp: Optional[float]
    total_ticks: int
    divergent_ticks: int
    max_volume_delta: float
    max_pressure_delta: float
    corridors_changed: list[str]
    constraints_removed: list[str]
    constraints_added: list[str]
    constraints_replaced: list[str]
    baseline_only_events: EventSummary
    replay_only_events: EventSummary
    conclusion: str


def _collect_event_summary(result: ReplayResult, side: str) -> EventSummary:
    """Collect unique events from one side across all divergence ticks."""
    by_kind: dict[str, set[str]] = {
        "constraint_expired": set(),
        "constraint_activated": set(),
        "corridor_opened": set(),
        "corridor_collapsed": set(),
        "field_collapsed": set(),
    }

    for div in result.divergences:
        events = div.baseline_only_events if side == "baseline" else div.replay_only_events
        for e in events:
            key = e.kind.value
            if key in by_kind:
                by_kind[key].add(e.name)

    return EventSummary(
        constraint_expired=sorted(by_kind["constraint_expired"]),
        constraint_activated=sorted(by_kind["constraint_activated"]),
        corridor_opened=sorted(by_kind["corridor_opened"]),
        corridor_collapsed=sorted(by_kind["corridor_collapsed"]),
        field_collapsed=sorted(by_kind["field_collapsed"]),
    )


def _generate_conclusion(result: ReplayResult, baseline_events: EventSummary, replay_events: EventSummary) -> str:
    """Generate a concise natural-language conclusion."""
    s = result.summary
    changes = result.changes

    parts: list[str] = []

    # What was changed
    change_descs: list[str] = []
    if changes.remove:
        change_descs.append(f"removed {', '.join(changes.remove)}")
    if changes.replace:
        change_descs.append(f"replaced {', '.join(changes.replace.keys())}")
    if changes.add:
        change_descs.append(f"added {', '.join(c.name for c in changes.add)}")

    if change_descs:
        parts.append(f"Replay {' and '.join(change_descs)}.")

    # Divergence
    if s.first_divergence_timestamp is not None:
        parts.append(f"First divergence at t={s.first_divergence_timestamp:.1f}.")
    else:
        parts.append("No divergence detected.")
        return " ".join(parts)

    # Pressure direction — derive from divergence records (summary stores abs values)
    divergent = [d for d in result.divergences if d.is_divergent]
    if divergent:
        # Use the signed delta with the largest absolute value
        peak = max(divergent, key=lambda d: abs(d.pressure_delta))
        if peak.pressure_delta > 0.01:
            parts.append(f"Replay shows up to {abs(peak.pressure_delta):.0%} more pressure.")
        elif peak.pressure_delta < -0.01:
            parts.append(f"Replay shows up to {abs(peak.pressure_delta):.0%} less pressure.")

    # Corridors
    if s.corridors_changed:
        parts.append(f"Most affected corridor(s): {', '.join(s.corridors_changed)}.")

    # Key event differences
    if baseline_events.constraint_expired:
        names = ", ".join(baseline_events.constraint_expired)
        parts.append(f"Baseline-only expirations: {names}.")

    if replay_events.constraint_expired:
        names = ", ".join(replay_events.constraint_expired)
        parts.append(f"Replay-only expirations: {names}.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_report(result: ReplayResult) -> ReplayReport:
    """Build a structured report from a ReplayResult."""
    s = result.summary
    baseline_events = _collect_event_summary(result, "baseline")
    replay_events = _collect_event_summary(result, "replay")
    conclusion = _generate_conclusion(result, baseline_events, replay_events)

    return ReplayReport(
        fork_timestamp=s.fork_timestamp,
        first_divergence_timestamp=s.first_divergence_timestamp,
        total_ticks=s.total_ticks,
        divergent_ticks=s.divergent_ticks,
        max_volume_delta=s.max_volume_delta,
        max_pressure_delta=s.max_pressure_delta,
        corridors_changed=list(s.corridors_changed),
        constraints_removed=list(result.changes.remove),
        constraints_added=[c.name for c in result.changes.add],
        constraints_replaced=list(result.changes.replace.keys()),
        baseline_only_events=baseline_events,
        replay_only_events=replay_events,
        conclusion=conclusion,
    )


def render_text(report: ReplayReport) -> str:
    """Render a ReplayReport as human-readable text."""
    lines: list[str] = []
    lines.append("=== VoidLine Replay Report ===")
    lines.append("")

    # Changes applied
    lines.append("Constraint changes:")
    if report.constraints_removed:
        lines.append(f"  removed:  {', '.join(report.constraints_removed)}")
    if report.constraints_replaced:
        lines.append(f"  replaced: {', '.join(report.constraints_replaced)}")
    if report.constraints_added:
        lines.append(f"  added:    {', '.join(report.constraints_added)}")
    if not report.constraints_removed and not report.constraints_replaced and not report.constraints_added:
        lines.append("  (none)")
    lines.append("")

    # Timeline
    lines.append("Timeline:")
    lines.append(f"  fork at:           t={report.fork_timestamp:.1f}")
    if report.first_divergence_timestamp is not None:
        lines.append(f"  first divergence:  t={report.first_divergence_timestamp:.1f}")
    else:
        lines.append("  first divergence:  (none)")
    lines.append(f"  divergent ticks:   {report.divergent_ticks} / {report.total_ticks}")
    lines.append("")

    # Pressure
    lines.append("Field impact:")
    lines.append(f"  max volume delta:   {report.max_volume_delta:+.3f}")
    lines.append(f"  max pressure delta: {report.max_pressure_delta:+.3f}")
    lines.append("")

    # Corridors
    lines.append("Corridors changed:")
    if report.corridors_changed:
        for c in report.corridors_changed:
            lines.append(f"  - {c}")
    else:
        lines.append("  (none)")
    lines.append("")

    # Events
    def _format_event_summary(es: EventSummary) -> list[str]:
        out: list[str] = []
        if es.constraint_expired:
            out.append(f"  expired:   {', '.join(es.constraint_expired)}")
        if es.constraint_activated:
            out.append(f"  activated: {', '.join(es.constraint_activated)}")
        if es.corridor_opened:
            out.append(f"  corridor opened:    {', '.join(es.corridor_opened)}")
        if es.corridor_collapsed:
            out.append(f"  corridor collapsed: {', '.join(es.corridor_collapsed)}")
        if es.field_collapsed:
            out.append(f"  field collapsed:    {', '.join(es.field_collapsed)}")
        if not out:
            out.append("  (none)")
        return out

    lines.append("Baseline-only events:")
    lines.extend(_format_event_summary(report.baseline_only_events))
    lines.append("")
    lines.append("Replay-only events:")
    lines.extend(_format_event_summary(report.replay_only_events))
    lines.append("")

    # Conclusion
    lines.append("Conclusion:")
    lines.append(f"  {report.conclusion}")
    lines.append("")

    return "\n".join(lines)
