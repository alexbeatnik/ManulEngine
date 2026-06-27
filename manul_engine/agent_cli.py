# manul_engine/agent_cli.py
"""Agent-facing CLI commands for external LLM / assistant drivers.

Mirrors ManulHeart's agent commands (`schema` / `map` / `read` / `run-step`):
each emits compact JSON to **stdout** (engine logs stay on stderr) so a driver
can pipe the output straight into a prompt. The browser commands attach to an
**already-running Chrome over CDP** (default ``http://127.0.0.1:9222``) — the
agent keeps one Chrome open and issues stateless CLI calls against it:

    # one-time: start Chrome with remote debugging, then:
    manul map --tab example.com
    manul run-step "Click the 'Login' button"
    manul read 'Order total'
    manul schema            # the DSL contract (no browser needed)

ManulEngine itself stays heuristics-first; these commands are the surface an
*external* model uses to see the page, act, and read — never CSS/XPath.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import sys

from .helpers import classify_step, detect_mode, extract_quoted
from .js_scripts import FULL_SCAN_JS

DEFAULT_CDP = "http://127.0.0.1:9222"
DEFAULT_MAX_PER_GROUP = 8

# Machine-readable outcome reasons (mirror ManulHeart's agent.Reason enum).
REASON_OK = "ok"
REASON_NOT_FOUND = "not_found"
REASON_VERIFY_FAILED = "verify_failed"
REASON_ACTION_FAILED = "action_failed"

_LOW_CONFIDENCE = 0.35


# ── output / arg helpers ─────────────────────────────────────────────────────


# The clean JSON payload goes here; engine chatter is redirected to stderr by
# ``agent_main`` so the two never mix on stdout. Set at the start of a command.
_PAYLOAD_STREAM = None


def emit_json(obj: object) -> None:
    """Write *obj* as indented JSON to the payload stream (the clean channel)."""
    stream = _PAYLOAD_STREAM or sys.stdout
    json.dump(obj, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
    stream.flush()


def _parse_flags(args: list[str], value_flags: set[str], bool_flags: set[str]) -> tuple[dict, list[str]]:
    """Tiny flag parser. Returns (flags, positionals)."""
    flags: dict[str, str | bool] = {}
    positionals: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in value_flags:
            flags[a] = args[i + 1] if i + 1 < len(args) else ""
            i += 2
        elif a in bool_flags:
            flags[a] = True
            i += 1
        else:
            positionals.append(a)
            i += 1
    return flags, positionals


async def _attach(cdp_url: str, tab: str):
    """Connect to a running Chrome over CDP and return (browser, page, engine)."""
    from .cdp import CDPBrowser
    from .core import ManulEngine

    browser = await CDPBrowser.connect_over_cdp(cdp_url)
    page = await browser.page_matching(tab)
    engine = ManulEngine(headless=True, disable_cache=True)
    return browser, page, engine


# ── schema ───────────────────────────────────────────────────────────────────


def engine_schema() -> dict:
    """The DSL grammar + agent JSON shapes — the engine's self-describing contract."""
    try:
        from importlib.metadata import version as _pkg_version

        ver = _pkg_version("manul-engine")
    except Exception:
        ver = "0.1.0"

    return {
        "engine": "manul-engine",
        "version": ver,
        "targeting": (
            "Elements are resolved by their human-visible label via a deterministic scorer — "
            "never CSS/XPath. Always quote labels: Click the 'Login' button."
        ),
        "hunt_rules": [
            "STEP headers are numbered; action lines under them are not.",
            "4-space indent under each STEP block.",
            "Never hardcode data: @var: {key} = value, reference as {key}.",
            "Follow Fill/Type with VERIFY that '<label>' has value '<expected>'.",
        ],
        "verbs": [
            {"verb": "NAVIGATE", "syntax": "NAVIGATE to <url>", "note": "load a page"},
            {"verb": "CLICK", "syntax": "Click the '<label>' button|link", "note": "click by label"},
            {"verb": "DOUBLE CLICK", "syntax": "DOUBLE CLICK the '<label>'"},
            {"verb": "RIGHT CLICK", "syntax": "RIGHT CLICK '<label>'"},
            {"verb": "FILL", "syntax": "Fill '<label>' with '<value>'", "note": "set an input; follow with VERIFY"},
            {"verb": "TYPE", "syntax": "Type '<value>' into '<label>'", "note": "keystroke-by-keystroke"},
            {"verb": "SELECT", "syntax": "Select '<option>' from the '<label>' dropdown"},
            {"verb": "HOVER", "syntax": "HOVER over the '<label>'"},
            {"verb": "DRAG", "syntax": "Drag the '<label>' and drop it into '<target>'"},
            {"verb": "PRESS", "syntax": "PRESS <key> [on '<label>']", "note": "e.g. PRESS Enter"},
            {"verb": "SCROLL", "syntax": "SCROLL DOWN|UP [inside '<container>']"},
            {"verb": "UPLOAD", "syntax": "UPLOAD '<path>' to '<label>'"},
            {
                "verb": "VERIFY",
                "syntax": "VERIFY that '<label>' is present|absent|enabled|disabled|checked",
                "note": "hard assertion; also: has text|value|placeholder '<expected>'",
            },
            {"verb": "VERIFY SOFTLY", "syntax": "VERIFY SOFTLY that '<label>' is present", "note": "non-fatal"},
            {"verb": "EXTRACT", "syntax": "EXTRACT the '<label>' into {var}", "note": "read text into a variable"},
            {"verb": "WAIT", "syntax": "WAIT <seconds>"},
            {"verb": "WAIT FOR", "syntax": "Wait for '<label>' to be visible|hidden"},
            {"verb": "WAIT FOR SELECTOR", "syntax": "WAIT FOR SELECTOR '<css>'"},
            {"verb": "WAIT FOR RESPONSE", "syntax": "WAIT FOR RESPONSE '<url-substr>'"},
            {"verb": "SET", "syntax": "SET {var} = <value>"},
            {"verb": "CALL PYTHON", "syntax": "CALL PYTHON <module.func>(<args>)", "note": "invoke a Python hook"},
            {"verb": "SCAN PAGE", "syntax": "SCAN PAGE [into {file}]", "note": "draft hunt steps for the page"},
            {"verb": "FULL SCAN", "syntax": "FULL SCAN", "note": "landmark-grouped control table"},
            {"verb": "MOCK", "syntax": "MOCK <METHOD> '<path>' with '<file>'"},
            {"verb": "IF", "syntax": "IF <condition>: … ELIF/ELSE … END IF"},
            {"verb": "REPEAT", "syntax": "REPEAT N TIMES: … END LOOP", "note": "{i} 0-based counter"},
            {"verb": "FOR EACH", "syntax": "FOR EACH {x} IN {list}: … END LOOP"},
            {"verb": "WHILE", "syntax": "WHILE <condition>: … END LOOP", "note": "capped at 100 iterations"},
            {"verb": "USE", "syntax": "USE <block> FROM '<library.hunt>'", "note": "import a reusable block"},
        ],
        "step_outcome": {
            "ok": "bool — step succeeded",
            "action": "string — classified step kind (click, fill, navigate, verify, extract, …)",
            "value": "string — value used/extracted (omitted when empty)",
            "url": "string — page URL after the step (omitted when unchanged)",
            "reason": "string — one of failure_reasons; 'ok' on success",
            "error": "string — raw error message (omitted on success)",
            "near": "array of {text, score} — top candidates on failure / low-confidence match",
        },
        "page_map": {
            "url": "string — current page URL",
            "groups": "array of {name, elements[], truncated}",
            "element": "{label, role, editable?}",
            "ordering": "Page first, then content landmarks, then chrome (header/nav/footer).",
        },
        "failure_reasons": [REASON_OK, REASON_NOT_FOUND, REASON_VERIFY_FAILED, REASON_ACTION_FAILED],
        "agent_commands": {
            "schema": "this contract",
            "map": "compact landmark-grouped page map → page_map JSON",
            "read": "read one labelled value (zero-scan) → {value, found, reason}",
            "read --selector": "sanitized region text → {text, selector}",
            "run-step": "run one instruction → step_outcome JSON",
        },
    }


async def cmd_schema(args: list[str]) -> int:
    _parse_flags(args, set(), {"--json"})  # --json accepted for symmetry; always JSON
    emit_json(engine_schema())
    return 0


# ── map ──────────────────────────────────────────────────────────────────────


def _group_rank(name: str) -> int:
    u = name.upper()
    if u == "PAGE":
        return 0
    if u.startswith("MAIN"):
        return 1
    if "SEARCH" in u or "RESULT" in u:
        return 2
    if u.startswith(("FORM", "DIALOG")):
        return 3
    if u.startswith(("ARTICLE", "SECTION")):
        return 4
    if u.startswith("HEADER") or "MASTHEAD" in u:
        return 7
    if u.startswith("NAV"):
        return 8
    if u.startswith(("ASIDE", "SIDEBAR")):
        return 9
    if u.startswith("FOOTER"):
        return 10
    return 5


def _compact_map(groups: dict, max_per_group: int, include_unlabeled: bool) -> dict:
    out_groups = []
    for name in sorted(groups.keys(), key=lambda n: (_group_rank(n), n)):
        seen: set[str] = set()
        kept: list[dict] = []
        for el in groups[name]:
            label = str(el.get("label", "")).strip()
            if not label and not include_unlabeled:
                continue
            key = label.lower() or f"{el.get('tag', '')}|{el.get('locator', '')}"
            if key in seen:
                continue
            seen.add(key)
            role = str(el.get("role", "")) or str(el.get("tag", ""))
            entry = {"label": label, "role": role}
            if el.get("editable"):
                entry["editable"] = True
            kept.append(entry)
        if not kept:
            continue
        group = {"name": name, "elements": kept[:max_per_group]}
        if len(kept) > max_per_group:
            group["truncated"] = len(kept) - max_per_group
        out_groups.append(group)
    return {"groups": out_groups}


async def cmd_map(args: list[str]) -> int:
    flags, _ = _parse_flags(args, {"--cdp", "--tab", "--max-per-group"}, {"--include-unlabeled", "--json"})
    cdp_url = str(flags.get("--cdp") or DEFAULT_CDP)
    tab = str(flags.get("--tab") or "")
    try:
        max_per_group = int(str(flags.get("--max-per-group") or DEFAULT_MAX_PER_GROUP))
    except ValueError:
        max_per_group = DEFAULT_MAX_PER_GROUP
    include_unlabeled = bool(flags.get("--include-unlabeled"))

    browser, page, _engine = await _attach(cdp_url, tab)
    try:
        raw = await page.evaluate(FULL_SCAN_JS)
        groups = json.loads(raw) if isinstance(raw, str) else (raw or {})
        page_map = _compact_map(groups, max_per_group, include_unlabeled)
        page_map = {"url": page.url or await page.evaluate("location.href"), **page_map}
        emit_json(page_map)
        return 0
    finally:
        await browser.close()


# ── read ─────────────────────────────────────────────────────────────────────


def _sanitize_text(raw: str) -> str:
    """Strip markup noise so an LLM isn't drowned in base64 / data-* / SVG paths."""
    if not raw:
        return ""
    cleaned: list[str] = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith(("data:image/", "data:text/")) or (len(line) > 80 and " " not in line and "-" not in line):
            continue
        if line.startswith(("data-", "jsaction=", "jscontroller=", "jsuid=")):
            continue
        if "M" in line and "Z" in line and len(line) > 100:
            continue
        if cleaned and cleaned[-1] == line:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def _truncate_text(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    dropped = len(text) - max_chars
    return text[:max_chars].rstrip(" \n") + f"\n[+{dropped} chars truncated]"


async def cmd_read(args: list[str]) -> int:
    flags, positionals = _parse_flags(args, {"--cdp", "--tab", "--selector", "--max-chars"}, {"--json"})
    cdp_url = str(flags.get("--cdp") or DEFAULT_CDP)
    tab = str(flags.get("--tab") or "")
    selector = str(flags.get("--selector") or "")
    try:
        max_chars = int(str(flags.get("--max-chars") or 0))
    except ValueError:
        max_chars = 0
    target = positionals[0] if positionals else ""

    if not target and not selector:
        print("Error: a target label or --selector is required.", file=sys.stderr)
        return 2

    browser, page, engine = await _attach(cdp_url, tab)
    try:
        if selector:
            el = await page.query(selector)
            text = await el.inner_text() if el is not None else ""
            text = _truncate_text(_sanitize_text(text), max_chars)
            emit_json({"text": text, "selector": selector})
            return 0

        step = f"EXTRACT the '{target}' into {{_agent_read}}"
        ok = await engine._handle_extract(page, step)
        value = str(engine.memory.get("_agent_read", "")) if ok else ""
        found = bool(ok and value)
        emit_json({"value": value, "found": found, "reason": REASON_OK if found else REASON_NOT_FOUND})
        return 0
    finally:
        await browser.close()


# ── run-step ─────────────────────────────────────────────────────────────────


# detect_mode → human-meaningful action name for the generic "action" kind.
_MODE_ACTION = {
    "input": "fill",
    "select": "select",
    "hover": "hover",
    "drag": "drag",
    "clickable": "click",
    "locate": "locate",
}


def _action_name(step: str, kind: str) -> str:
    """A specific, human-meaningful action verb for the outcome."""
    if kind != "action":
        return kind
    if "double" in step.lower():
        return "double_click"
    return _MODE_ACTION.get(detect_mode(step), "click")


async def _near_candidates(engine, page, step: str) -> list[dict]:
    """Top-3 candidate labels (with 0..1 confidence) for a target step."""
    from .core import _confidence

    targets = extract_quoted(step, preserve_case=False)
    if not targets:
        return []
    mode = detect_mode(step)
    if mode == "locate":
        mode = "clickable"
    try:
        raw = await engine._snapshot(page, mode, [t.lower() for t in targets])
        scored = engine._score_elements(raw, step, mode, targets, None, False)
    except Exception:
        return []
    out: list[dict] = []
    for cand in scored[:3]:
        name = str(cand.get("name", "")).strip()
        if not name:
            continue
        out.append({"text": name, "score": round(_confidence(int(cand.get("score", 0) or 0)), 3)})
    return out


async def _run_one(engine, page, step: str) -> dict:
    """Execute one DSL instruction and build the compact StepOutcome dict."""
    kind = classify_step(step)
    url_before = page.url
    ok = True
    error: str | None = None
    value = ""

    try:
        if kind == "navigate":
            ok = await engine._handle_navigate(page, step)
        elif kind == "verify":
            ok = await engine._handle_verify(page, step)
        elif kind == "verify_softly":
            ok = await engine._handle_verify_softly(page, step)
        elif kind == "extract":
            ok = await engine._handle_extract(page, step)
            if ok:
                var = extract_quoted(step) or []
                value = str(engine.memory.get("_agent_read", "")) or (var[0] if var else "")
        elif kind == "press":
            ok = await engine._handle_press(page, step)
        elif kind == "press_enter":
            ok = await engine._handle_press_enter(page)
        elif kind == "right_click":
            ok = await engine._handle_right_click(page, step)
        elif kind == "upload":
            ok = await engine._handle_upload(page, step)
        elif kind == "scroll":
            await engine._handle_scroll(page, step)
        elif kind == "wait":
            import re

            n = re.search(r"(\d+)", step)
            await asyncio.sleep(int(n.group(1)) if n else 2)
        else:
            ok = await engine._execute_step(page, step)
            quoted = extract_quoted(step)
            if quoted and detect_mode(step) == "input":
                value = quoted[-1]
    except Exception as exc:
        ok = False
        error = str(exc)

    try:
        url_after = await page.evaluate("location.href")
    except Exception:
        url_after = url_before

    reason = (
        REASON_OK if ok else (REASON_VERIFY_FAILED if kind in ("verify", "verify_softly") else REASON_ACTION_FAILED)
    )

    outcome: dict = {"ok": ok, "step": step, "action": _action_name(step, kind), "reason": reason}
    if value:
        outcome["value"] = value
    if url_after and url_after != url_before:
        outcome["url"] = url_after
    if error:
        outcome["error"] = error

    # Surface top candidates on failure OR on a low-confidence "success", so an
    # agent can tell a fuzzy match landed on the wrong element (mirrors ManulHeart).
    if extract_quoted(step):
        near = await _near_candidates(engine, page, step)
        top = near[0]["score"] if near else 0.0
        if near:
            outcome["score"] = top
        if not ok:
            if near:
                outcome["near"] = near
            if reason == REASON_ACTION_FAILED and (not near or top < _LOW_CONFIDENCE):
                outcome["reason"] = REASON_NOT_FOUND
        elif top and top < _LOW_CONFIDENCE:
            outcome["near"] = near
    return outcome


async def cmd_run_step(args: list[str]) -> int:
    flags, positionals = _parse_flags(args, {"--cdp", "--tab"}, {"--json", "--compact"})
    cdp_url = str(flags.get("--cdp") or DEFAULT_CDP)
    tab = str(flags.get("--tab") or "")
    step = positionals[0] if positionals else ""
    if not step:
        print("Error: a DSL instruction is required, e.g. run-step \"Click the 'Login' button\".", file=sys.stderr)
        return 2

    browser, page, engine = await _attach(cdp_url, tab)
    try:
        outcome = await _run_one(engine, page, step)
        emit_json(outcome)
        return 0 if outcome["ok"] else 1
    finally:
        await browser.close()


# ── dispatch ─────────────────────────────────────────────────────────────────

_COMMANDS = {
    "schema": cmd_schema,
    "map": cmd_map,
    "read": cmd_read,
    "run-step": cmd_run_step,
}


async def agent_main(command: str, args: list[str]) -> int:
    """Dispatch an agent subcommand. Returns a process exit code.

    Engine output (``print``/logs) is redirected to **stderr** for the duration
    of the command so that stdout carries only the JSON payload — exactly how a
    driver pipes ``manul map`` / ``run-step`` into a prompt.
    """
    global _PAYLOAD_STREAM

    handler = _COMMANDS.get(command)
    if handler is None:
        print(f"Error: unknown agent command {command!r}.", file=sys.stderr)
        return 2

    _PAYLOAD_STREAM = sys.stdout
    try:
        with contextlib.redirect_stdout(sys.stderr):
            return await handler(args)
    except Exception as exc:
        print(f"Error: {command} failed: {exc}", file=sys.stderr)
        return 1
    finally:
        _PAYLOAD_STREAM = None
