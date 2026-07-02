# EXTENSION_ENGINE_CONTRACT

This document specifies the runtime contract between the ManulEngine VS Code
extension (TypeScript) and the backing CLI engine. It is implemented by **both**
runtimes — ManulEngine (Python, `manul-engine`) and ManulEngine (Go, `ManulEngineGo`)
— which expose the same `manul` CLI surface, argv shapes, env vars,
stdout/stdin debug protocol, and exit-code semantics. Kept in sync across both
engine repos and the extension.

Every behavior below was extracted directly from the extension's source tree
under [src/](src/). For any new engine implementation, preserving the argv
shapes, environment variables, stdout/stdin wire protocol, exit-code
semantics, and filesystem artifacts described here is **mandatory** — the
extension has no feature flag or negotiation layer and will break silently if
the engine deviates.

The extension pins an exact minimum engine version:

```
MIN_MANUL_ENGINE_VERSION = "0.1.0"        // src/shared/index.ts:5
MIN_MANUL_ENGINE_GO_VERSION  = "0.1.0"      // src/shared/index.ts:6
```

The version-check path parses the first `\d+(?:\.\d+)+` run out of `manul --version`
stdout ([src/huntRunner.ts:37-56](src/huntRunner.ts#L37-L56)).

---

## 1. CLI Invocations & Arguments

All invocations go through one of three spawn paths:

| Path | Function | Call site |
|---|---|---|
| Piped `child_process.spawn` | `runHunt`, `runHuntFileDebugPanel`, `runExplain`, `manul scan` | [src/huntRunner.ts](src/huntRunner.ts), [src/explainLensProvider.ts](src/explainLensProvider.ts), [src/stepBuilderPanel.ts](src/stepBuilderPanel.ts) |
| One-shot `child_process.execFile` | version probe, doctor, shell `where`/`command -v` lookup | [src/huntRunner.ts](src/huntRunner.ts), [src/manulDoctor.ts](src/manulDoctor.ts) |
| Integrated terminal (`vscode.window.createTerminal` + `sendText`) | interactive `--debug`, raw run, `record`, `daemon` | [src/huntRunner.ts:562-584](src/huntRunner.ts#L562-L584), [src/huntTestController.ts:462-486](src/huntTestController.ts#L462-L486), [src/stepBuilderPanel.ts:1039-1050](src/stepBuilderPanel.ts#L1039-L1050), [src/schedulerPanel.ts:371-385](src/schedulerPanel.ts#L371-L385) |

### 1.1 Executable resolution

`findManulExecutable(workspaceRoot)` in [src/huntRunner.ts:125-267](src/huntRunner.ts#L125-L267)
resolves the `manul` executable in this order:

1. `manulEngine.manulPath` VS Code setting if it exists on disk.
2. `<workspaceRoot>/{.venv,venv,env,.env}/{bin/manul|Scripts/manul.exe}`
3. Unix: `~/.local/bin/manul` → macOS `~/Library/Python/<ver>/bin/manul` → `~/.local/pipx/venvs/manul-engine/bin/manul` → `/opt/homebrew/bin/manul` → `/usr/local/bin/manul` → `/usr/bin/manul`
4. Windows: `%APPDATA%/Python/<ver>/Scripts/manul.exe`, `%LOCALAPPDATA%/Programs/Python/<ver>/Scripts/manul.exe`
5. Async login-shell lookup: `where manul` (Windows), `<shell> -l -i -c 'command -v manul'` (bash/zsh/ksh), `fish -l -c 'command -v manul'` (fish), `sh -c 'command -v manul'` (sh/dash/ash). 3-second timeout.
6. Final fallback: the bare string `"manul"`.

The Go rewrite must preserve the **binary name `manul`** and respond to the
same subcommand surface on **stdout**, not via an alternate IPC socket —
every spawn in the extension drives the process directly through pipes.

### 1.2 `manul --version`

- `execFile(manulExe, ["--version"], { timeout: 5000 })` — [src/huntRunner.ts:37](src/huntRunner.ts#L37)
- **Expected stdout**: a line matching `/(\d+(?:\.\d+)+)/`. First regex capture is treated as the installed version. Example: `manul 0.1.0`.
- No stderr contract. A timeout or missing match is treated as "version unknown" (no warning shown).

### 1.3 Hunt-file runs (the core contract)

The canonical spawn is built by `buildSpawnConfig` at
[src/huntRunner.ts:284-331](src/huntRunner.ts#L284-L331).

**Argv layout (in the exact order the extension emits):**

```
manul [--browser <name>] --workers 1
      [--break-lines <line1,line2,...>]
      [--retries <N>]
      [--screenshot <mode>]
      [--html-report]
      [--explain]
      <absolute-path-to-hunt-file>
```

Observations:
- `--workers 1` is **always present** for runs spawned by `runHunt` /
  `runHuntFileDebugPanel`. The VS Code concurrency setting
  (`manulEngine.workers`, clamped `[1,16]`) controls the number of **parallel
  processes** the extension launches, not the engine-level `--workers` value
  ([src/huntTestController.ts:19-45](src/huntTestController.ts#L19-L45)).
- The hunt file is passed as the **final positional argument** as an
  absolute filesystem path.
- `cwd` for the child is the VS Code workspace folder that owns the file,
  falling back to `path.dirname(huntFile)`.

**Conditional flags:**

| Flag | Condition | Value source |
|---|---|---|
| `--browser chromium\|firefox\|webkit\|electron` | `manulEngine.browser` explicitly set in workspace/user settings; omitted when unset so JSON config wins | [src/huntRunner.ts:71-90](src/huntRunner.ts#L71-L90) |
| `--browser chromium` (+ `MANUL_CHANNEL=chrome\|msedge` env) | `manulEngine.browser` = `chrome` or `msedge` | same |
| `--break-lines <csv>` | Any enabled `vscode.SourceBreakpoint` exists inside the hunt file; line numbers are 1-based | [src/huntRunner.ts:593-599](src/huntRunner.ts#L593-L599) |
| `--retries <N>` | `manulEngine.retries > 0` | [src/huntRunner.ts:301-302](src/huntRunner.ts#L301-L302) |
| `--screenshot <mode>` | `manulEngine.screenshotMode` ≠ `"on-fail"` (the default is omitted) | [src/huntRunner.ts:304-305](src/huntRunner.ts#L304-L305) |
| `--html-report` | `manulEngine.htmlReport === true` | [src/huntRunner.ts:307](src/huntRunner.ts#L307) |
| `--explain` | `manulEngine.explainMode === true` **or** the debug-panel runner (`forceExplain`) | [src/huntRunner.ts:309-312](src/huntRunner.ts#L309-L312) |

**Engine behavior required:**
- `--break-lines` **must** cause the engine to emit the pause protocol
  (§3.1/§4) before executing any step whose 1-based source-file line number
  matches. Without the pause protocol, pipe-mode runs hang because the
  extension deadlocks its own pipe runner ([src/huntTestController.ts:180-183](src/huntTestController.ts#L180-L183)).
- `--explain` **must** cause the engine to emit the inline explain heuristics
  block described in §3.3 and respond to the `explain-next` stdin token (§4.3).
- `--workers 1` inside the engine is expected to serialize steps for
  deterministic ordering; the extension parallelizes at the process level.

### 1.4 Interactive debug in a terminal

File: [src/huntRunner.ts:562-584](src/huntRunner.ts#L562-L584). Sent verbatim
via `terminal.sendText` (POSIX or PowerShell quoting applied):

```
<manulExe> [--browser <X>] --debug [--break-lines <csv>] <huntFile>
```

The engine in this mode is expected to drive an **interactive prompt on
stdin** (readline-style) where typing `h` triggers an in-browser "highlight
target" action (`terminal.sendText("h")` — [src/extension.ts:308-325](src/extension.ts#L308-L325)).
This path does **not** speak the `\x00MANUL_DEBUG_PAUSE\x00` protocol;
`--debug` is the interactive-terminal variant, whereas pipe-mode pause uses
`--break-lines` alone.

### 1.5 Raw run in a terminal

File: [src/huntTestController.ts:462-486](src/huntTestController.ts#L462-L486).

```
<manulExe> <huntFile>
```

No flags beyond positional args. PowerShell gets `& ` prefix.

### 1.6 `manul scan`

File: [src/stepBuilderPanel.ts:919-956](src/stepBuilderPanel.ts#L919-L956).

```
manul scan <url> <outputFile>
```

- `stdio: ["ignore", "ignore", "pipe"]` — **stdout is discarded**; stderr is
  captured for error display only.
- Timeout: 90 s (hard kill).
- Success contract: exit 0 **and** the file at `<outputFile>` exists.
- `<outputFile>` is always `<tests_home>/draft.hunt` (see §5).

### 1.7 `manul record`

File: [src/stepBuilderPanel.ts:1039-1050](src/stepBuilderPanel.ts#L1039-L1050).
Sent via `terminal.sendText`:

```
"<manulExe>" record '<url>'
```

Interactive long-running session; no return contract, extension does not
read its output.

### 1.8 `manul daemon`

File: [src/schedulerPanel.ts:371-385](src/schedulerPanel.ts#L371-L385). Sent
via `terminal.sendText`:

```
"<manulExe>" daemon '<testsHome>' --headless
```

- `<testsHome>` is absolute, derived from `tests_home` in the JSON config.
- The engine is expected to honor `@schedule:` headers inside `.hunt` files
  found under `<testsHome>`.
- Daemon lifecycle = terminal lifecycle. The extension has no shutdown
  protocol — it disposes the `Manul Daemon` named terminal (SIGHUP).

### 1.9 Doctor (diagnostic probes — out of engine scope)

File: [src/manulDoctor.ts](src/manulDoctor.ts). These probe the host Python
install, not ManulEngine (Go), but any Go rewrite that drops Python should update
the diagnostic or it will show a misleading ⚠️:

- `python3 -c "import sys; print(sys.version.split(' ')[0])"` (falls back to `python`)
- `python3 -c "import manul; print(manul.__version__)"`
- `python3 -m playwright --version`

---

## 2. Environment Variables

All vars are injected into the child `env` by `buildSpawnConfig`
([src/huntRunner.ts:321-328](src/huntRunner.ts#L321-L328)) and the
explain-lens spawn ([src/explainLensProvider.ts:157-161](src/explainLensProvider.ts#L157-L161)).
The child inherits `process.env` first, then the extension overlays:

| Variable | Value (string) | When set | Purpose |
|---|---|---|---|
| `PYTHONUNBUFFERED` | `"1"` | **Always** (from `PYTHON_ENV_FLAGS`, [src/constants.ts:38](src/constants.ts#L38)) | Force line-buffered stdout so the extension's stdout parser sees markers immediately. A Go rewrite must also flush stdout on every newline — the extension relies on this invariant. |
| `MANUL_CHANNEL` | `"chrome"` or `"msedge"` | User selected a Chromium channel via `manulEngine.browser` | Overrides JSON-config channel without needing the config file. |
| `MANUL_AUTO_ANNOTATE` | `"true"` (main) / `"1"` (explain-lens path) | `manulEngine.autoAnnotate === true` | Engine-side AI auto-annotation of selectors. **Note: the value string differs between code paths**; a robust engine should treat any non-empty truthy value as enabled. |
| `MANUL_VERIFY_MAX_RETRIES` | `String(<integer>)` | `manulEngine.verifyMaxRetries` is non-null | Override for `VERIFY` soft-wait retry count. |
| `MANUL_EXECUTABLE_PATH` | trimmed string from JSON config | `executable_path` exists in `manul_engine_configuration.json` | Path to a user-provided browser executable (e.g. Electron binary). |

No other `MANUL_*` variables are written by the extension. Everything else
the engine reads must be configured via `manul_engine_configuration.json`
(see §5.3).

---

## 3. Standard I/O & IPC (CRITICAL)

All pipe-mode runs use `{ stdio: ["pipe", "pipe", "pipe"] }`. Stdout and
stderr are both fed into `onData` — the engine's stderr is not parsed
separately.

### 3.1 Line buffering & safety limits

Implemented in [src/huntRunner.ts:407-424](src/huntRunner.ts#L407-L424):

- The extension line-buffers stdout by splitting on `"\n"` (LF). Windows
  `\r\n` survives because the `\r` stays at line end — the extension strips
  neither. **Engines should emit `\n` line terminators.**
- Per-line safety cap: **1 MB** (`MAX_LINE_LEN = 1_048_576`). Lines longer
  than this are discarded wholesale.
- Per-marker JSON payload cap: **512 KB** (`MAX_JSON_LEN = 524_288`).
  Payloads over this are silently dropped.

### 3.2 Block start/pass/fail markers (test-explorer reporting)

Regex: [src/shared/index.ts:43](src/shared/index.ts#L43)

```
BLOCK_LOG_RE = /^\s*\[(?:[^\]]*\s+)?BLOCK\s+(START|PASS|FAIL)\]\s+(.+?)\s*$/i
```

Matching lines are consumed by `parseEngineLogLine` and converted to a
`TestBlock { id, status }` — `status` is `running`, `pass`, or `fail`.
Canonical line shapes the engine should emit:

```
[BLOCK START] <block-id>
[BLOCK PASS] <block-id>
[BLOCK FAIL] <block-id>
```

The optional `[<prefix> BLOCK START]` capture group allows a leading
timestamp or level tag (e.g. `[2026-04-20 12:00:00 BLOCK START] login`) but
the keyword `BLOCK` and bracket delimiters are mandatory. Block IDs must be
stable per-instance so the extension can open/close them correctly.

The extension tracks nested blocks and disambiguates repeated IDs by
appending `#<count>` ([src/huntTestController.ts:99-140](src/huntTestController.ts#L99-L140)).

### 3.3 Step / action / explain-block markers

Regexes in [src/shared/index.ts:41](src/shared/index.ts#L41) and
[src/explainHoverProvider.ts:103-107](src/explainHoverProvider.ts#L103-L107):

```
STEP_LINE_RE          = /(?:\[[^\]]*\s*)?(STEP\s+\d+)(?:\s*[:@][^\]]*\])?\s*[:\s]\s*(.+)/i
BRACKETED_STEP_MARKER = /\[(?:[^\]]*\s)?STEP\s+(\d+)(?:\s*[@:\]])/i
PLAIN_STEP_MARKER     = /^\s*STEP\s+(\d+)\b/i
ACTION_START_RE       = /^\s*\[(?:[^\]]*\s)?ACTION START\]/i
EXPLAIN_START_RE      = /^\s*┌─(?:\s*🔍)?\s*EXPLAIN:/u
EXPLAIN_END_RE        = /^\s*└─(?:\s*✅)?\s*Decision:/iu
```

Canonical engine output shapes the parser expects:

```
[🐾 STEP 3 @hunt.login]  (or any bracket containing "STEP <N>" before a @ or :)
STEP 3: Click the Login button
[ACTION START] ...
┌─ 🔍 EXPLAIN: <freeform diagnostics, multiple lines>
│  ...
└─ ✅ Decision: <text>
```

- The EXPLAIN block is captured verbatim (start line through end line) and
  stored keyed to the file line of the N-th executable step as computed by
  `buildStepLineMap` ([src/explainHoverProvider.ts:27-59](src/explainHoverProvider.ts#L27-L59)).
- Emission of `┌─` and `└─` box-drawing characters is part of the contract.
  Replace the decorative `🔍` / `✅` at will, but the leading `┌─` / `└─`
  and the literal words `EXPLAIN:` / `Decision:` are required.
- A code-fence sanitizer neutralizes ```` ``` ```` inside the captured block
  ([src/explainHoverProvider.ts:214](src/explainHoverProvider.ts#L214)) —
  engines can still emit triple backticks; they'll be rendered inert.

### 3.4 Pause marker (breakpoint hit, stdin handshake)

Literal string constant:

```
PAUSE_MARKER = "\x00MANUL_DEBUG_PAUSE\x00"            // src/shared/index.ts:23
```

**Wire format** (exactly one `\n`-terminated line):

```
\x00MANUL_DEBUG_PAUSE\x00{"step":"<verbatim-step-text>","idx":<1-based-int>}\n
```

- Marker may be preceded by arbitrary prefix characters on the same line —
  the parser uses `line.indexOf(PAUSE_MARKER)` and takes everything after
  the marker as JSON ([src/huntRunner.ts:439-455](src/huntRunner.ts#L439-L455)).
- JSON payload schema:
  ```ts
  interface PausePayload {
    step: string;   // the step's source-text; may contain spaces, quotes, unicode
    idx: number;    // 1-based step index within the executable plan body
  }
  ```
  Malformed JSON is tolerated (the extension defaults `step=""`, `idx=0`
  and still sends a stdin response so the engine is not deadlocked). The
  engine **must** still accept the response in that degraded case.
- **Re-emission rule**: if the engine emits `PAUSE_MARKER` again while the
  extension is still waiting for the user's choice (e.g. because an
  `explain-next` handler also prints the marker after its response), the
  extension ignores the duplicate (`pauseActive` flag,
  [src/huntRunner.ts:413-444](src/huntRunner.ts#L413-L444)). The engine
  **must** re-emit the marker after every `explain-next` response so the
  pause stays live.

### 3.5 Explain-next result marker

Literal:

```
EXPLAIN_NEXT_MARKER = "\x00MANUL_EXPLAIN_NEXT\x00"   // src/shared/index.ts:24
```

Wire format (one `\n`-terminated line):

```
\x00MANUL_EXPLAIN_NEXT\x00<json-payload>\n
```

JSON schema — `ExplainNextResult`
([src/shared/index.ts:27-40](src/shared/index.ts#L27-L40)):

```ts
interface ExplainNextResult {
  step: string;                        // echo of the step that was explained
  score: number;                       // normalized confidence, [0.0, 1.0]
  confidence_label: string;            // freeform, e.g. "high" / "medium" / "low"
  target_found: boolean;
  target_element: string | null;       // null when no element matched
  explanation: string;                 // freeform text
  risk: string;                        // freeform text; "" is acceptable
  suggestion: string | null;           // null when no suggestion
  heuristic_score: number | null;      // raw heuristic, [0.0, 1.0], or null
  heuristic_match: string | null;      // freeform match description, or null
}
```

Parser: [src/huntRunner.ts:427-436](src/huntRunner.ts#L427-L436). Invalid
JSON is silently dropped — no stdin response is expected for this marker.

### 3.6 Lines not matching any marker

All other stdout/stderr lines are forwarded verbatim (with a synthesized
`"\n"` appended) to the `onData` callback, which routes them to either the
Test Explorer's `run.appendOutput` stream (CRLF-normalized) or to a
`vscode.OutputChannel`. **No other line pattern is parsed.**

### 3.7 Exit codes

[src/huntRunner.ts:354](src/huntRunner.ts#L354), [src/huntTestController.ts:184-220](src/huntTestController.ts#L184-L220), [src/explainLensProvider.ts:108-112](src/explainLensProvider.ts#L108-L112):

| Code | Meaning |
|---|---|
| `0` | Success → `run.passed(item)`, "✅ Explain run complete." |
| any non-zero (including `null` on signal, which the extension rewrites to `1`) | Failure → `run.failed(item, …)` with `"Exit code: <code>\n<captured output>"` |

The engine **must** exit with a non-zero code on any hunt-file failure,
including assertion failures, timeout, and user abort. No distinction is
drawn between codes — the extension does not branch on specific values.

### 3.8 Cancellation / abort

- `token.onCancellationRequested` → `proc.kill()` and resolve(1)
  ([src/huntRunner.ts:357-360](src/huntRunner.ts#L357-L360), [src/huntRunner.ts:550-553](src/huntRunner.ts#L550-L553)).
- Default signal: Node's `ChildProcess.kill()` = **SIGTERM** on POSIX,
  `TerminateProcess` on Windows. The engine should clean up and exit
  promptly on SIGTERM.
- "Stop Test" during a paused debug session: the extension writes
  `"abort\n"` to stdin, waits **500 ms**, then sends SIGTERM
  ([src/huntRunner.ts:520-525](src/huntRunner.ts#L520-L525)). The engine
  should honor `abort\n` as a graceful-exit request; unresponsive engines
  are SIGTERM'd after the grace period.

---

## 4. The Debug Protocol

End-to-end sequence (pipe-mode, `runHuntFileDebugPanel`):

```
┌─────────────┐                                ┌─────────────┐
│  Extension  │                                │   Engine    │
└──────┬──────┘                                └──────┬──────┘
       │  spawn: manul --workers 1 --break-lines … --explain <file>
       │────────────────────────────────────────────▶│
       │                                             │  (reaches line N)
       │  \x00MANUL_DEBUG_PAUSE\x00{"step":"…","idx":N}\n
       │◀────────────────────────────────────────────│
       │  (show QuickPick to user)                   │
       │                                             │
       │  (optional) "explain-next\n"                │
       │────────────────────────────────────────────▶│
       │  \x00MANUL_EXPLAIN_NEXT\x00{…payload…}\n    │
       │◀────────────────────────────────────────────│
       │  \x00MANUL_DEBUG_PAUSE\x00{…same…}\n  ← re-emit
       │◀────────────────────────────────────────────│
       │                                             │
       │  "next\n" | "continue\n" | "debug-stop\n" | "abort\n"
       │────────────────────────────────────────────▶│
       │                                             │  (resumes)
```

### 4.1 When the engine must pause

- A VS Code breakpoint is set on the line (passed as `--break-lines <n>`;
  see §1.3).
- **Not** for `DEBUG` / `PAUSE` DSL keywords in pipe-mode runs — those
  produce pauses only when `--debug` (terminal) is used. The pipe runner
  does not set `--debug`.

### 4.2 Gutter-breakpoint protocol summary

1. Extension collects 1-based line numbers from `vscode.debug.breakpoints`
   (`SourceBreakpoint`, enabled, matching fsPath) via `getHuntBreakpointLines`
   ([src/huntRunner.ts:593-599](src/huntRunner.ts#L593-L599)).
2. Extension passes them as `--break-lines <csv>`.
3. Engine prints the pause marker line immediately **before** executing
   each matching step.
4. Engine blocks on `stdin.readline()` for the response token.

VS Code shows unverified (grey) breakpoints because the extension ships no
DAP adapter; this is expected and must not be "fixed" by emitting DAP
frames.

### 4.3 Stdin response tokens (exact bytes)

All tokens are written by the extension with a literal `"\n"` terminator
([src/huntRunner.ts:460-531](src/huntRunner.ts#L460-L531)).

| Token written | UI trigger | Meaning for the engine |
|---|---|---|
| `next\n` | ⏭ **Next Step** QuickPick item, **ESC**, or programmatic abort via `onDidHide` | Execute the paused step, then pause again at the next breakpoint. |
| `continue\n` | ▶ **Continue All** QuickPick item | Remove / ignore all remaining breakpoints for this run; execute to end. |
| `debug-stop\n` | ⏹ **Debug Stop** QuickPick item | Clear all breakpoints but continue the run (engine-side state mutation — the process keeps running). |
| `abort\n` | 🛑 **Stop Test** QuickPick item | Graceful abort; engine should cleanup and exit non-zero. Extension SIGTERMs after 500 ms if the process is still alive. |
| `explain-next\n` | 🔮 **Explain Next Step** QuickPick item (no `stepOverride`) | Run heuristic scoring on the **currently paused** step, emit `EXPLAIN_NEXT_MARKER` payload, then re-emit `PAUSE_MARKER`. Do **not** advance execution. |
| `explain-next {"step":"<override>"}\n` | 🔮 **Explain Next Step** when the user has edited the line in the editor since the pause | Same as above but score the provided `step` text instead of the one in the pause payload. Payload is strict JSON, single line. |

**Important pipeline guarantees:**
- The response token **must** be a full newline-terminated string.
- After an `explain-next` request, the engine must emit `EXPLAIN_NEXT_MARKER`
  then re-emit `PAUSE_MARKER` so the stepper stays paused. The extension's
  `pauseActive` flag deduplicates the second marker only within the current
  pause cycle.
- Writes happen via `proc.stdin.write(...)`. `stdin` is closed only when
  the extension kills the process. Engines should **not** exit on EOF during
  a pause.

### 4.4 Terminal-mode debug (`--debug`)

Out-of-protocol. The engine drives a plain readline prompt in the terminal;
the extension only types the literal character `h` + Enter to request
target highlighting ([src/extension.ts:322-325](src/extension.ts#L322-L325)).

### 4.5 Pause-timeout fallback

- Setting: `manulEngine.debugPauseTimeoutSeconds` (default **300**).
- On timeout, the extension writes `continue\n` to stdin and reports a
  status-bar message ([src/huntRunner.ts:489-509](src/huntRunner.ts#L489-L509)).
- A value of `0` disables the timeout.

---

## 5. File System Artifacts

All paths are resolved relative to the **first workspace folder's fsPath**
unless stated otherwise.

### 5.1 `manul_engine_configuration.json` (read by extension)

The filename is configurable via the VS Code setting
`manulEngine.configFile`; the default is
`DEFAULT_CONFIG_FILENAME = "manul_engine_configuration.json"`
([src/shared/index.ts:22](src/shared/index.ts#L22),
[src/constants.ts:70-76](src/constants.ts#L70-L76)).

Fields the extension **reads** from this file (writes only happen through
the Config panel — see [src/configPanel.ts:9-37](src/configPanel.ts#L9-L37)):

| Key | Type | Consumer | Default |
|---|---|---|---|
| `executable_path` | `string` | `MANUL_EXECUTABLE_PATH` env export | — |
| `controls_cache_dir` | `string` (abs or rel) | Cache TreeView root | `"cache"` |
| `tests_home` | `string` (abs or rel) | `manul scan` output dir, `manul daemon` arg | `"tests"` |
| `workers` | `number` | Fallback for extension-level parallelism when `manulEngine.workers` is unset | `4` |

All other keys in `DEFAULT_CONFIG` (e.g. `model`, `headless`, `browser`,
`channel`, `browser_args`, `timeout`, `nav_timeout`, `ai_always`, `ai_policy`,
`ai_threshold`, `controls_cache_enabled`, `semantic_cache_enabled`,
`log_name_maxlen`, `log_thought_maxlen`, `auto_annotate`,
`custom_controls_dirs`, `retries`, `screenshot`, `html_report`,
`verify_max_retries`, `explain_mode`) are round-tripped by the Config panel
but **not otherwise read by the extension** — they are the engine's
concern. A Go rewrite should continue to honor these keys.

### 5.2 `reports/run_history.json` (read by extension, written by engine)

Path: `<workspaceRoot>/reports/run_history.json`
([src/schedulerPanel.ts:119](src/schedulerPanel.ts#L119)).

**Format: JSON Lines (one JSON object per line).** Parser splits on `\n`
and tolerates blank / malformed lines.

**Record schema** — `RunHistoryRecord`:

```ts
interface RunHistoryRecord {
  file: string;          // absolute or workspace-relative hunt file path
  name: string;          // short display name (usually the basename)
  timestamp: string;     // must be Date.parse()-able, i.e. ISO-8601 recommended
  status: string;        // one of: "pass" | "fail" | "flaky" | "warning"
                         //   (any other value is rendered as green "pass")
  duration_ms: number;   // finite Number (milliseconds)
}
```

Validation: `isRunHistoryRecord`
([src/schedulerPanel.ts:39-52](src/schedulerPanel.ts#L39-L52)) — all five
fields must be present with the correct type, non-empty strings, and a
parseable timestamp; records failing validation are dropped silently.

Read mode: up to the last 512 KB of the file are tail-read to avoid
unbounded memory; the last **5 records per file** are retained
([src/schedulerPanel.ts:115-176](src/schedulerPanel.ts#L115-L176)).

**Engine contract:** append exactly one JSON object per newline,
**never** pretty-print multi-line JSON, never overwrite — the extension
only appends-reads.

### 5.3 Cache directory (read by extension)

Path: resolved from `controls_cache_dir` (JSON config); default
`<workspaceRoot>/cache`. Layout expected by the Cache TreeView
([src/cacheTreeProvider.ts:94-155](src/cacheTreeProvider.ts#L94-L155)):

```
<cache-dir>/
├── <site-A>/             ← direct child dirs become TreeView "site" nodes
│   ├── <page-1>/         ← grandchild dirs become "page" nodes
│   │   └── <any files>   ← counted via recursive walkFiles()
│   └── <page-2>/
├── <site-B>/
└── run_*                 ← **ignored** (child dirs whose name starts with "run_")
```

The extension deletes via `fs.rmSync(dirPath, { recursive: true, force: true })`
for "Clear site cache" and "Clear all cache" user actions.

### 5.4 `manul scan` output

File: `<tests_home>/draft.hunt` (computed in
[src/stepBuilderPanel.ts:907-910](src/stepBuilderPanel.ts#L907-L910)).

- The engine must create this file as a valid `.hunt` document (UTF-8,
  newline-terminated lines, DSL conformant).
- Existence is used by the extension as a success signal — it opens the
  file with `vscode.workspace.openTextDocument` after the scan completes.

### 5.5 HTML reports (`--html-report`)

Not read by the extension. The `--html-report` flag is forwarded to the
engine, which is expected to emit a report in an engine-determined
location. No path is asserted on the extension side.

### 5.6 `.hunt` files (read by extension for discovery & diagnostics)

- Discovery glob: `**/*.hunt` excluding `**/{node_modules,.venv,dist}/**`
  ([src/huntTestController.ts:246](src/huntTestController.ts#L246)).
- Scheduler scans `**/*.hunt` excluding `**/node_modules/**`
  ([src/schedulerPanel.ts:62](src/schedulerPanel.ts#L62)).
- Front-matter recognized: `@context:`, `@title:`, `@blueprint:`, `@var:`,
  `@script:`, `@tags:`, `@data:`, `@schedule:`.
- Hook blocks: `[SETUP] ... [END SETUP]`, `[TEARDOWN] ... [END TEARDOWN]`.

The DSL grammar the extension validates against is encoded in
[src/shared/manul-dsl-contract.json](src/shared/manul-dsl-contract.json) and
enforced by [src/shared/huntValidator.ts](src/shared/huntValidator.ts). The
engine must execute a strict superset of that grammar; mismatches surface as
editor diagnostics but do not block spawning.

---

## Appendix A — Wire-format Quick Reference

| Direction | Literal bytes | Followed by | Terminator |
|---|---|---|---|
| engine → ext | `\x00MANUL_DEBUG_PAUSE\x00` | `{"step":"…","idx":N}` | `\n` |
| engine → ext | `\x00MANUL_EXPLAIN_NEXT\x00` | `<ExplainNextResult JSON>` | `\n` |
| engine → ext | `[BLOCK START] <id>` / `[BLOCK PASS] <id>` / `[BLOCK FAIL] <id>` | — | `\n` |
| engine → ext | `┌─ 🔍 EXPLAIN:` … `└─ ✅ Decision: …` | multi-line block | `\n`-per-line |
| engine → ext | `[🐾 STEP N @…]` or `STEP N: <desc>` | — | `\n` |
| ext → engine | `next` | — | `\n` |
| ext → engine | `continue` | — | `\n` |
| ext → engine | `debug-stop` | — | `\n` |
| ext → engine | `abort` | — | `\n` |
| ext → engine | `explain-next` | optional ` {"step":"…"}` | `\n` |
| ext → engine (terminal `--debug`) | `h` | — | `\n` (via `sendText`) |

All bytes are UTF-8. The engine must flush stdout after every `\n`
(`PYTHONUNBUFFERED=1` is injected to guarantee this for the Python
implementation; a Go implementation should either disable stdout buffering
or flush on every `Println`).

## Appendix B — Exit-code Quick Reference

| Exit | Extension treatment |
|---|---|
| `0` | Success |
| non-zero (or `null` from signal, rewritten to `1`) | Failure |

## Appendix C — Engine Version Gate

If `manul --version` reports a version whose dotted components are
component-wise **less than** the detected runtime's minimum
(`MIN_MANUL_ENGINE_VERSION` for Python, `MIN_MANUL_ENGINE_GO_VERSION` for Go
— both currently `0.1.0`), the extension raises a warning toast:

> `v<installed> is installed but this extension requires <ManulEngine | ManulEngine (Go)> >= v0.1.0.`
> followed by `Run: pip install --upgrade "manul-engine==0.1.0"` (Python) or `Run: go build -o manul ./cmd/manul` (Go)

([src/huntRunner.ts:35-58](src/huntRunner.ts#L35-L58)). An engine
implementation must continue to respond to `--version` on stdout with a
parseable `\d+(?:\.\d+)+` token — and must report a version **≥ 0.1.0**, or
bump the constants in [src/shared/index.ts:5-6](src/shared/index.ts#L5-L6) in
lockstep.
