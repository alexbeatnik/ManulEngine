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
  --yellow:    #f9e2af;
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
.stat-card.flaky  .value  { color: var(--yellow); }

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
.pass-bar .seg-pass  { background: var(--green); }
.pass-bar .seg-flaky { background: var(--yellow); }
.pass-bar .seg-fail  { background: var(--red); }

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
.badge-flaky { background: rgba(249,226,175,0.15); color: var(--yellow); }

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

/* ── Steps table ──────────────────────── */

.steps-table {
  width: 100%;
  border-collapse: collapse;
}
.steps-table th {
  text-align: left;
  font-size: 0.7rem;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 8px 16px;
  background: var(--surface2);
  border-bottom: 1px solid var(--border);
}
.steps-table td {
  padding: 8px 16px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
.steps-table tr:last-child td { border-bottom: none; }

.step-pass td:first-child { border-left: 3px solid var(--green); }
.step-fail td:first-child { border-left: 3px solid var(--red); }
.step-skip td:first-child { border-left: 3px solid var(--text-dim); }

.step-fail { background: rgba(243,139,168,0.05); }

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

/* ── Footer ───────────────────────────── */

.footer {
  margin-top: 32px;
  text-align: center;
  font-size: 0.75rem;
  color: var(--text-dim);
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
});
"""


# ── HTML template helpers ─────────────────────────────────────────────────────

def _esc(text: str | None) -> str:
    """HTML-escape a string (or return empty string for None)."""
    return html.escape(str(text)) if text else ""


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


def _render_step_row(step: StepResult) -> str:
    """Render a single <tr> for a step."""
    css_class = f"step-{step.status}"
    status_class = f"status-{step.status}"
    status_label = step.status.upper()

    # Build cell content for the step text column
    text_html = f'<span class="step-text">{_esc(step.text)}</span>'
    if step.error:
        text_html += f'\n<div class="step-error">{_esc(step.error)}</div>'
    if step.screenshot:
        text_html += (
            f'\n<div class="step-screenshot">'
            f'<img src="data:image/png;base64,{step.screenshot}" '
            f'alt="Screenshot step {step.index}" title="Click to expand" />'
            f'</div>'
        )

    return (
        f'<tr class="{css_class}">'
        f'<td>{step.index}</td>'
        f'<td>{text_html}</td>'
        f'<td class="step-status {status_class}">{status_label}</td>'
        f'<td class="step-duration">{_fmt_duration(step.duration_ms)}</td>'
        f'</tr>'
    )


def _render_mission(mission: MissionResult) -> str:
    """Render one mission accordion block."""
    status = mission.status
    icon = {"pass": "\u2705", "fail": "\u274c", "flaky": "\u26a0\ufe0f"}.get(status, "\u2753")
    badge_class = f"badge-{status}"

    meta_parts = [_fmt_duration(mission.duration_ms)]
    if mission.attempts > 1:
        meta_parts.append(f"{mission.attempts} attempts")

    steps_html = ""
    if mission.steps:
        rows = "\n".join(_render_step_row(s) for s in mission.steps)
        steps_html = (
            f'<table class="steps-table">'
            f'<thead><tr><th>#</th><th>Step</th><th>Status</th><th>Time</th></tr></thead>'
            f'<tbody>{rows}</tbody>'
            f'</table>'
        )
        if mission.attempts > 1:
            label = "passed on retry" if status == "flaky" else "after retries"
            steps_html += f'<div class="attempts-note">\U0001f504 {label} (attempt {mission.attempts}/{mission.attempts})</div>'
    elif mission.error:
        steps_html = f'<div class="step-error" style="margin:12px 16px;">{_esc(mission.error)}</div>'

    return (
        f'<div class="mission">'
        f'  <div class="mission-header">'
        f'    <span class="chevron">\u25b6</span>'
        f'    <span class="icon">{icon}</span>'
        f'    <span class="name">{_esc(mission.name)}</span>'
        f'    <span class="badge {badge_class}">{status}</span>'
        f'    <span class="meta">{" \u00b7 ".join(meta_parts)}</span>'
        f'  </div>'
        f'  <div class="mission-body">{steps_html}</div>'
        f'</div>'
    )


def _render_html(summary: RunSummary) -> str:
    """Build the complete HTML document from a RunSummary."""
    total = summary.total or 1  # avoid division by zero
    pass_rate = ((summary.passed + summary.flaky) / total) * 100
    pass_pct = (summary.passed / total) * 100
    flaky_pct = (summary.flaky / total) * 100
    fail_pct = (summary.failed / total) * 100

    missions_html = "\n".join(_render_mission(m) for m in summary.missions)

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
  <div class="stat-card flaky">
    <div class="value">{summary.flaky}</div>
    <div class="label">Flaky</div>
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
    {summary.passed} passed \u00b7 {summary.flaky} flaky \u00b7 {summary.failed} failed
  </div>
  <div class="pass-bar">
    <div class="seg-pass" style="width:{pass_pct:.1f}%"></div>
    <div class="seg-flaky" style="width:{flaky_pct:.1f}%"></div>
    <div class="seg-fail" style="width:{fail_pct:.1f}%"></div>
  </div>
</div>

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
