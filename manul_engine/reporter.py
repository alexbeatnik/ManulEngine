# manul_engine/reporter.py
"""
Self-contained HTML report generator for ManulEngine test runs.

Generates a single ``manul_report.html`` file with:
  - Inline CSS (dark theme) and JavaScript (no external dependencies)
  - Dashboard stats: total / passed / failed / flaky / duration / pass-rate bar
  - Interactive accordion: click a mission row to expand its step list
  - Base64 screenshots embedded inline next to corresponding steps
  - Error messages / stack traces on failed steps

Usage::

    from manul_engine.reporter  import generate_report
    from manul_engine.reporting import RunSummary

    generate_report(summary, "manul_report.html")
"""

from __future__ import annotations

import html
import os
import re
from pathlib import Path

from .reporting import RunSummary, MissionResult, StepResult


# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """\
:root {
  --bg:        #1e1e2e;
  --surface:   #262637;
  --surface2:  #2e2e42;
  --border:    #3a3a52;
  --text:      #cdd6f4;
  --text-dim:  #8b8fa7;
  --accent:    #89b4fa;
  --green:     #a6e3a1;
  --red:       #f38ba8;
  --orange:    #fab387;
  --yellow:    #f9e2af;
  --teal:      #94e2d5;
  --radius:    8px;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  font-size: 14px;
  line-height: 1.6;
  padding: 24px;
  max-width: 1100px;
  margin: 0 auto;
}

h1 {
  font-size: 1.6rem;
  font-weight: 700;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 10px;
}
h1 .logo { font-size: 1.8rem; }

.subtitle {
  color: var(--text-dim);
  font-size: 0.85rem;
  margin-bottom: 20px;
}

.session-banner {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin: -6px 0 20px;
}

.session-chip {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text);
  font-size: 0.78rem;
  padding: 6px 10px;
}

.session-chip strong {
  color: var(--accent);
}

/* ── Dashboard ────────────────────────── */

.dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 16px;
  text-align: center;
}
.stat-card .value {
  font-size: 1.8rem;
  font-weight: 700;
}
.stat-card .label {
  font-size: 0.75rem;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 2px;
}
.stat-card.passed .value  { color: var(--green); }
.stat-card.failed .value  { color: var(--red); }
.stat-card.broken .value  { color: var(--orange); }
.stat-card.flaky  .value  { color: var(--yellow); }
.stat-card.warning .value { color: var(--yellow); }

/* ── Pass-rate bar ────────────────────── */

.pass-bar-container {
  margin-bottom: 24px;
}
.pass-bar-label {
  font-size: 0.8rem;
  color: var(--text-dim);
  margin-bottom: 4px;
}
.pass-bar {
  background: var(--surface);
  border-radius: 6px;
  overflow: hidden;
  height: 22px;
  display: flex;
}
.pass-bar .seg-pass    { background: var(--green); }
.pass-bar .seg-broken  { background: var(--orange); }
.pass-bar .seg-flaky   { background: var(--yellow); }
.pass-bar .seg-warning { background: var(--yellow); }
.pass-bar .seg-fail    { background: var(--red); }

/* ── Mission list ─────────────────────── */

.mission {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin-bottom: 8px;
  overflow: hidden;
}

.mission-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  gap: 10px;
  transition: background 0.15s;
}
.mission-header:hover { background: var(--surface2); }

.mission-header .chevron {
  font-size: 0.7rem;
  color: var(--text-dim);
  transition: transform 0.2s;
  width: 14px;
  flex-shrink: 0;
}
.mission.open .chevron { transform: rotate(90deg); }

.mission-header .icon { font-size: 1.1rem; flex-shrink: 0; }
.mission-header .name { flex: 1; font-weight: 600; }
.mission-header .badge {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.badge-pass  { background: rgba(166,227,161,0.15); color: var(--green); }
.badge-fail  { background: rgba(243,139,168,0.15); color: var(--red); }
.badge-broken { background: rgba(250,179,135,0.15); color: var(--orange); }
.badge-flaky { background: rgba(249,226,175,0.15); color: var(--yellow); }
.badge-warning { background: rgba(249,226,175,0.15); color: var(--yellow); }

.mission-header .meta {
  font-size: 0.8rem;
  color: var(--text-dim);
  white-space: nowrap;
}

.mission-body {
  display: none;
  border-top: 1px solid var(--border);
  padding: 0;
}
.mission.open .mission-body { display: block; }

/* ── Steps list ───────────────────────── */

.steps-list { width: 100%; }

.step-row {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border);
}
.step-row:last-child { border-bottom: none; }

.step-index {
  width: 24px;
  flex-shrink: 0;
  color: var(--text-dim);
  font-size: 0.8rem;
  padding-top: 2px;
}

.step-content { flex: 1; min-width: 0; }

.step-row.step-pass { border-left: 3px solid var(--green); }
.step-row.step-fail {
  border-left: 3px solid var(--red);
  background: rgba(243,139,168,0.05);
}
.step-row.step-skip { border-left: 3px solid var(--text-dim); }
.step-row.step-warning {
  border-left: 3px solid var(--yellow);
  background: rgba(249,226,175,0.05);
}

.step-status {
  width: 60px;
  flex-shrink: 0;
  font-weight: 600;
  font-size: 0.8rem;
  white-space: nowrap;
  padding-top: 2px;
}

.step-duration {
  width: 60px;
  flex-shrink: 0;
  font-size: 0.8rem;
  color: var(--text-dim);
  white-space: nowrap;
  text-align: right;
  padding-top: 2px;
}

.step-text {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 0.82rem;
  word-break: break-word;
}
.step-error {
  margin-top: 6px;
  padding: 8px 10px;
  background: rgba(243,139,168,0.08);
  border: 1px solid rgba(243,139,168,0.2);
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.75rem;
  color: var(--red);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
}

.step-screenshot {
  margin-top: 8px;
}
.step-screenshot img {
  max-width: 100%;
  max-height: 300px;
  border-radius: 4px;
  border: 1px solid var(--border);
  cursor: pointer;
  transition: max-height 0.3s;
}
.step-screenshot img.expanded {
  max-height: none;
}

.step-status {
  font-weight: 600;
  font-size: 0.8rem;
  white-space: nowrap;
}
.status-pass { color: var(--green); }
.status-fail { color: var(--red); }
.status-skip { color: var(--text-dim); }
.status-warning { color: var(--yellow); }

/* ── Healed indicator ─────────────────── */

.healed-badge {
  display: inline-block;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 8px;
  background: rgba(148,226,213,0.15);
  color: var(--teal);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-left: 8px;
  vertical-align: middle;
}

.step-duration {
  font-size: 0.8rem;
  color: var(--text-dim);
  white-space: nowrap;
}

.attempts-note {
  font-size: 0.75rem;
  color: var(--yellow);
  padding: 6px 16px 10px;
}

/* ── Logical step groups ──────────────── */

details.lstep-block {
  border-top: 1px solid var(--border);
}
details.lstep-block:first-of-type {
  border-top: none;
}

.lstep-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 16px;
  background: var(--surface2);
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  user-select: none;
  list-style: none;
}
.lstep-header::-webkit-details-marker { display: none; }
.lstep-header .lstep-chevron {
  font-size: 0.65rem;
  color: var(--text-dim);
  transition: transform 0.2s;
  width: 12px;
  flex-shrink: 0;
}
details.lstep-block[open] .lstep-chevron { transform: rotate(90deg); }
.lstep-body { padding-left: 24px; }
.lstep-header .lstep-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 0.02em;
}
.lstep-header .lstep-count {
  margin-left: auto;
  font-size: 0.72rem;
  color: var(--text-dim);
}
.lstep-header .lstep-status {
  font-size: 0.72rem;
  font-weight: 700;
}
.lstep-status-pass  { color: var(--green); }
.lstep-status-fail  { color: var(--red); }
.lstep-status-warning { color: var(--yellow); }

/* ── Soft errors block ────────────────── */

.soft-errors {
  margin: 8px 16px 12px;
  padding: 10px 14px;
  background: rgba(249,226,175,0.08);
  border: 1px solid rgba(249,226,175,0.25);
  border-radius: 6px;
}
.soft-errors-title {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--yellow);
  margin-bottom: 6px;
}
.soft-errors ul {
  margin: 0;
  padding-left: 18px;
  font-size: 0.75rem;
  color: var(--yellow);
  list-style: disc;
}
.soft-errors li {
  margin-bottom: 3px;
}

/* ── Footer ───────────────────────────── */

.footer {
  margin-top: 32px;
  text-align: center;
  font-size: 0.75rem;
  color: var(--text-dim);
}

/* ── Control Panel ────────────────────── */

.control-panel {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 16px;
  margin-bottom: 16px;
}
.control-panel label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}
.control-panel input[type="checkbox"] {
  accent-color: var(--accent);
  width: 15px;
  height: 15px;
  cursor: pointer;
}

.tag-chips {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.tag-chip {
  font-family: inherit;
  font-size: 0.72rem;
  padding: 3px 10px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-dim);
  cursor: pointer;
  user-select: none;
  transition: all 0.15s;
}
.tag-chip:hover {
  border-color: var(--accent);
  color: var(--text);
}
.tag-chip.active {
  background: rgba(137,180,250,0.18);
  border-color: var(--accent);
  color: var(--accent);
  font-weight: 600;
}
.tag-divider {
  width: 1px;
  height: 20px;
  background: var(--border);
  flex-shrink: 0;
}
"""


# ── JavaScript ────────────────────────────────────────────────────────────────

_JS = """\
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.mission-header').forEach(h => {
    h.addEventListener('click', () => {
      h.closest('.mission').classList.toggle('open');
    });
  });
  document.querySelectorAll('.step-screenshot img').forEach(img => {
    img.addEventListener('click', () => img.classList.toggle('expanded'));
  });

  /* ── Control panel: Show Only Failed ─────────── */
  var failCb = document.getElementById('filter-failed');
  var warnCb = document.getElementById('filter-warnings');
  var activeTag = null;
  function applyFilters() {
    var onlyFailed = failCb && failCb.checked;
    var showWarnings = warnCb && warnCb.checked;
    document.querySelectorAll('.mission').forEach(function(m) {
      var status = m.getAttribute('data-status');
      var tags = (m.getAttribute('data-tags') || '').split(',').filter(Boolean);
      var show = true;
      if (onlyFailed && status !== 'fail') show = false;
      if (showWarnings && status !== 'warning' && status !== 'fail') show = false;
      if (activeTag && tags.indexOf(activeTag) === -1) show = false;
      m.style.display = show ? '' : 'none';
    });
  }
  if (failCb) failCb.addEventListener('change', function() { if (failCb.checked && warnCb) warnCb.checked = false; applyFilters(); });
  if (warnCb) warnCb.addEventListener('change', function() { if (warnCb.checked && failCb) failCb.checked = false; applyFilters(); });

  /* ── Control panel: Tag chips ────────────────── */
  document.querySelectorAll('.tag-chip').forEach(function(chip) {
    chip.addEventListener('click', function() {
      var tag = chip.getAttribute('data-tag');
      if (activeTag === tag) {
        activeTag = null;
        chip.classList.remove('active');
      } else {
        document.querySelectorAll('.tag-chip.active').forEach(function(c) {
          c.classList.remove('active');
        });
        activeTag = tag;
        chip.classList.add('active');
      }
      applyFilters();
    });
  });
});
"""


# ── HTML template helpers ─────────────────────────────────────────────────────

def _esc(text: str | None) -> str:
    """HTML-escape a string (or return empty string for None)."""
    if text is None:
        return ""
    return html.escape(str(text))


def _fmt_duration(ms: float) -> str:
    """Format milliseconds to a human-readable string."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    secs = ms / 1000
    if secs < 60:
        return f"{secs:.1f}s"
    mins = int(secs // 60)
    remaining = secs % 60
    return f"{mins}m {remaining:.0f}s"


def _render_step_row(step: StepResult, local_index: int | None = None) -> str:
    """Render a single flex-row div for a step.

    *local_index* — when supplied, overrides ``step.index`` for the # column.
    This avoids confusing gaps when STEP marker lines were counted in the
    plan enumeration but produced no StepResult.
    """
    css_class = f"step-{step.status}"
    status_class = f"status-{step.status}"
    status_label = step.status.upper()
    display_index = local_index if local_index is not None else step.index

    # Strip any legacy numbered prefix ("2. ") from the step text so it is
    # never shown in the report regardless of the source hunt file format.
    display_text = re.sub(r'^\s*\d+\.\s*', '', step.text)

    content_html = f'<div class="step-text">{_esc(display_text)}</div>'
    if step.healed:
        content_html += '<span class="healed-badge">\U0001fa79 healed</span>'
    if step.error:
        content_html += f'\n<div class="step-error">{_esc(step.error)}</div>'
    if step.screenshot:
        content_html += (
            f'\n<div class="step-screenshot">'
            f'<img src="data:image/png;base64,{step.screenshot}" '
            f'alt="Screenshot step {display_index}" title="Click to expand" />'
            f'</div>'
        )

    return (
        f'<div class="step-row {css_class}">'
        f'<div class="step-index">{display_index}</div>'
        f'<div class="step-content">{content_html}</div>'
        f'<div class="step-status {status_class}">{status_label}</div>'
        f'<div class="step-duration">{_fmt_duration(step.duration_ms)}</div>'
        f'</div>'
    )


def _group_steps(steps: list[StepResult]) -> list[tuple[str | None, list[StepResult]]]:
    """Partition a flat step list into (label, [steps]) groups.

    Steps that precede any STEP marker go into the ``None`` group.
    Returns a single-element list with label ``None`` when no STEP markers exist,
    allowing the caller to fall back to the flat rendering.
    """
    groups: list[tuple[str | None, list[StepResult]]] = []
    current_label: str | None = None
    bucket: list[StepResult] = []
    for s in steps:
        if s.logical_step != current_label:
            if bucket:
                groups.append((current_label, bucket))
            current_label = s.logical_step
            bucket = []
        bucket.append(s)
    if bucket:
        groups.append((current_label, bucket))
    return groups


def _render_lstep_group(label: str | None, steps: list[StepResult], index: int) -> str:
    """Render one logical-step accordion block containing a steps table.

    Uses a native ``<details>/<summary>`` element — no JavaScript required.
    Passing groups start collapsed; failing groups start expanded so errors
    are immediately visible.
    """
    has_failure = any(s.status == "fail" for s in steps)
    has_warning = any(s.status == "warning" for s in steps)
    has_healed = any(s.healed for s in steps)
    if has_failure:
        status_text = "FAIL"
        status_class = "lstep-status-fail"
    elif has_warning:
        status_text = "WARNING"
        status_class = "lstep-status-warning"
    else:
        status_text = "PASS"
        status_class = "lstep-status-pass"
    healed_marker = ' <span class="healed-badge">\U0001fa79 healed</span>' if has_healed and not has_failure else ""
    display_label = _esc(label) if label else "Default"
    open_attr = " open" if has_failure else ""
    # Use 1-based local indices so the # column reads 1, 2, 3… within each
    # STEP group rather than the global plan position (which has gaps where
    # STEP marker lines were counted but produced no StepResult).
    rows = "\n".join(_render_step_row(s, local_index=i) for i, s in enumerate(steps, 1))
    return (
        f'<details class="lstep-block"{open_attr}>'
        f'  <summary class="lstep-header">'
        f'    <span class="lstep-chevron">&#9658;</span>'
        f'    <span class="lstep-label">{display_label}</span>'
        f'    <span class="lstep-count">{len(steps)} action{"s" if len(steps) != 1 else ""}</span>'
        f'    <span class="lstep-status {status_class}">{status_text}</span>{healed_marker}'
        f'  </summary>'
        f'  <div class="lstep-body"><div class="steps-list">{rows}</div></div>'
        f'</details>'
    )


def _render_mission(mission: MissionResult) -> str:
    """Render one mission accordion block, with optional logical-step grouping."""
    status = mission.status
    icon = {"pass": "\u2705", "fail": "\u274c", "broken": "\U0001f4a5", "flaky": "\u26a0\ufe0f", "warning": "\u26a0\ufe0f"}.get(status, "\u2753")
    badge_class = f"badge-{status}"
    tags_attr = _esc(",".join(mission.tags)) if mission.tags else ""

    meta_parts = [_fmt_duration(mission.duration_ms)]
    if mission.attempts > 1:
        meta_parts.append(f"{mission.attempts} attempts")

    meta_text = " \u00b7 ".join(meta_parts)
    steps_html = ""
    if mission.steps:
        groups = _group_steps(mission.steps)
        # Use flat rendering when no STEP markers were used (single None group).
        if len(groups) == 1 and groups[0][0] is None:
            rows = "\n".join(
                _render_step_row(s, local_index=i)
                for i, s in enumerate(groups[0][1], 1)
            )
            steps_html = f'<div class="steps-list">{rows}</div>'
        else:
            steps_html = "\n".join(
                _render_lstep_group(label, grp, i)
                for i, (label, grp) in enumerate(groups)
            )
        if mission.attempts > 1:
            label_txt = "passed on retry" if status == "flaky" else "after retries"
            steps_html += f'<div class="attempts-note">\U0001f504 {label_txt} (attempt {mission.attempts})</div>'
        # Render soft assertion warnings
        if mission.soft_errors:
            items = "".join(f"<li>{_esc(e)}</li>" for e in mission.soft_errors)
            steps_html += (
                f'<div class="soft-errors">'
                f'<div class="soft-errors-title">\u26a0\ufe0f Soft Assertion Warnings ({len(mission.soft_errors)})</div>'
                f'<ul>{items}</ul>'
                f'</div>'
            )
    elif mission.error:
        steps_html = f'<div class="step-error" style="margin:12px 16px;">{_esc(mission.error)}</div>'

    return (
        f'<div class="mission" data-status="{_esc(status)}" data-tags="{tags_attr}">'
        f'  <div class="mission-header">'
        f'    <span class="chevron">\u25b6</span>'
        f'    <span class="icon">{icon}</span>'
        f'    <span class="name">{_esc(mission.name)}</span>'
        f'    <span class="badge {badge_class}">{status}</span>'
        f'    <span class="meta">{meta_text}</span>'
        f'  </div>'
        f'  <div class="mission-body">{steps_html}</div>'
        f'</div>'
    )


def _render_html(summary: RunSummary) -> str:
    """Build the complete HTML document from a RunSummary."""
    total = summary.total or 1  # avoid division by zero
    pass_rate = ((summary.passed + summary.flaky + summary.warning) / total) * 100
    pass_pct = (summary.passed / total) * 100
    broken_pct = (summary.broken / total) * 100
    flaky_pct = (summary.flaky / total) * 100
    warning_pct = (summary.warning / total) * 100
    fail_pct = (summary.failed / total) * 100

    # Collect unique tags across all missions for the filter UI
    all_tags: list[str] = sorted({t for m in summary.missions for t in m.tags})

    missions_html = "\n".join(_render_mission(m) for m in summary.missions)

    # Build control panel HTML
    tag_chips_html = ""
    if all_tags:
        chips = "".join(
            f'<button type="button" class="tag-chip" data-tag="{_esc(t)}">{_esc(t)}</button>'
            for t in all_tags
        )
        tag_chips_html = f'<span class="tag-divider"></span><div class="tag-chips">{chips}</div>'

    control_panel_html = (
        f'<div class="control-panel">'
        f'<label><input type="checkbox" id="filter-failed"> Show only failed</label>'
        f'<label><input type="checkbox" id="filter-warnings"> Show warnings</label>'
        f'{tag_chips_html}'
        f'</div>'
    )

    session_banner_html = (
      f'<div class="session-banner">'
      f'  <div class="session-chip"><strong>Run Session</strong> {_esc(summary.session_id)}</div>'
      f'  <div class="session-chip">Merged invocations: {max(1, int(summary.invocation_count or 1))}</div>'
      f'</div>'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ManulEngine Test Report</title>
<style>{_CSS}</style>
</head>
<body>

<h1><span class="logo">\U0001f43e</span> ManulEngine Test Report</h1>
<div class="subtitle">
  {_esc(summary.started_at)} &mdash; {_fmt_duration(summary.duration_ms)} total
</div>
{session_banner_html}

<!-- Dashboard -->
<div class="dashboard">
  <div class="stat-card">
    <div class="value">{summary.total}</div>
    <div class="label">Total</div>
  </div>
  <div class="stat-card passed">
    <div class="value">{summary.passed}</div>
    <div class="label">Passed</div>
  </div>
  <div class="stat-card failed">
    <div class="value">{summary.failed}</div>
    <div class="label">Failed</div>
  </div>
  <div class="stat-card broken">
    <div class="value">{summary.broken}</div>
    <div class="label">Broken</div>
  </div>
  <div class="stat-card flaky">
    <div class="value">{summary.flaky}</div>
    <div class="label">Flaky</div>
  </div>
  <div class="stat-card warning">
    <div class="value">{summary.warning}</div>
    <div class="label">Warning</div>
  </div>
  <div class="stat-card">
    <div class="value">{pass_rate:.0f}%</div>
    <div class="label">Pass Rate</div>
  </div>
  <div class="stat-card">
    <div class="value">{_fmt_duration(summary.duration_ms)}</div>
    <div class="label">Duration</div>
  </div>
</div>

<!-- Pass-rate bar -->
<div class="pass-bar-container">
  <div class="pass-bar-label">
    {summary.passed} passed \u00b7 {summary.flaky} flaky \u00b7 {summary.warning} warning \u00b7 {summary.broken} broken \u00b7 {summary.failed} failed
  </div>
  <div class="pass-bar">
    <div class="seg-pass" style="width:{pass_pct:.1f}%"></div>
    <div class="seg-broken" style="width:{broken_pct:.1f}%"></div>
    <div class="seg-flaky" style="width:{flaky_pct:.1f}%"></div>
    <div class="seg-warning" style="width:{warning_pct:.1f}%"></div>
    <div class="seg-fail" style="width:{fail_pct:.1f}%"></div>
  </div>
</div>

<!-- Control Panel -->
{control_panel_html}

<!-- Missions -->
{missions_html}

<div class="footer">
  Generated by ManulEngine \u00b7 {_esc(summary.ended_at)}
</div>

<script>{_JS}</script>
</body>
</html>"""


# ── Public API ────────────────────────────────────────────────────────────────

def generate_report(summary: RunSummary, output_path: str) -> str:
    """Generate a self-contained HTML report and write it to *output_path*.

    Returns the absolute path of the written file.
    """
    html_content = _render_html(summary)
    out = Path(output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_content, encoding="utf-8")
    return str(out)
