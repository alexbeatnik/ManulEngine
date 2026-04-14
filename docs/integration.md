# Integration

> **ManulEngine v0.0.9.29**

This document covers integrating ManulEngine with Python code, CI/CD pipelines, Docker, and the companion MCP Server.

## Python API (`ManulSession`)

`ManulSession` is an async context manager for pure-Python browser automation. It manages the Playwright lifecycle and routes every call through the full ManulEngine heuristic pipeline — no selectors needed.

### Basic usage

```python
from manul_engine import ManulSession

async with ManulSession(headless=True) as session:
    await session.navigate("https://example.com/login")
    await session.fill("Username field", "admin")
    await session.fill("Password field", "secret")
    await session.click("Log in button")
    await session.verify("Welcome")

    price = await session.extract("Product Price")
    print(f"Price: {price}")
```

### Constructor parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `model` | `None` | Ollama model name (`None` = heuristics-only) |
| `headless` | `False` | Hide the browser window |
| `browser` | `"chromium"` | `"chromium"`, `"firefox"`, or `"webkit"` |
| `browser_args` | `[]` | Extra browser launch flags |
| `ai_threshold` | `None` | Score threshold for LLM fallback |
| `disable_cache` | `False` | Disable persistent controls cache |
| `semantic_cache` | `True` | Enable in-session semantic cache |
| `channel` | `None` | Installed browser channel |
| `executable_path` | `None` | Path to Electron / custom browser |

### Core methods

All methods are async and route through the heuristic scoring pipeline:

```python
await session.navigate(url)                      # load URL
await session.click(target, double=False)        # click / double-click
await session.fill(target, text)                 # type into a field
await session.select(option, target)             # dropdown selection
await session.hover(target)                      # hover
await session.drag(source, destination)           # drag and drop
await session.right_click(target)                # right-click
await session.press(key, target=None)            # key press
await session.upload(file_path, target)          # file upload
await session.scroll(target=None)                # scroll page or container
await session.verify(target, present=True, enabled=None, checked=None)
await session.extract(target, variable=None)     # extract text
await session.wait(seconds)                      # hard sleep
```

### Mixing Python API with DSL snippets

```python
async with ManulSession() as session:
    await session.navigate("https://example.com")

    result = await session.run_steps("""
        STEP 1: Search
            FILL 'Search' with 'ManulEngine'
            PRESS Enter
            VERIFY that 'Results' is present
    """)
    assert result.status == "pass"
```

`run_steps()` executes raw DSL text against the current open page without restarting the browser.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `session.page` | `Page` | Active Playwright Page object |
| `session.engine` | `ManulEngine` | Underlying engine instance |
| `session.memory` | `ScopedVariables` | Variable store |

### Integration with pytest

```python
import asyncio
import pytest
from manul_engine import ManulSession

@pytest.fixture
async def session():
    async with ManulSession(headless=True) as s:
        yield s

@pytest.mark.asyncio
async def test_login(session):
    await session.navigate("https://www.saucedemo.com")
    await session.fill("Username", "standard_user")
    await session.fill("Password", "secret_sauce")
    await session.click("Login button")
    await session.verify("Products")
```

### Using EngineConfig

For full configuration control, pass an `EngineConfig` object:

```python
from manul_engine import ManulSession, EngineConfig

config = EngineConfig(
    headless=True,
    browser="firefox",
    controls_cache_enabled=True,
    timeout=10000,
)
# EngineConfig can also be loaded from a file:
# config = EngineConfig.from_file("manul_engine_configuration.json")

engine = ManulEngine(config=config)
```

### When to use ManulSession vs .hunt files

| Use case | Recommendation |
|----------|----------------|
| Pure Python automation / scripting | `ManulSession` |
| Existing pytest suites | `ManulSession` |
| RPA scripts with heavy Python logic | `ManulSession` |
| Shared QA artifacts readable by non-technical team | `.hunt` files |
| VS Code Test Explorer / debug features | `.hunt` files |
| Scheduled monitoring | `.hunt` files with `@schedule:` |

---

## Global Lifecycle Hooks

For suite-wide setup and teardown (database seeding, auth tokens, environment prep), use lifecycle hooks in `manul_hooks.py`:

```python
# tests/manul_hooks.py
from manul_engine import before_all, after_all, GlobalContext

@before_all
def setup(ctx: GlobalContext) -> None:
    """Runs once before all hunt files in the directory."""
    ctx.variables["TOKEN"] = auth_service.get_token()
    ctx.variables["BASE_URL"] = "https://staging.example.com"

@after_all
def teardown(ctx: GlobalContext) -> None:
    """Runs once after all hunt files complete."""
    auth_service.revoke_token(ctx.variables["TOKEN"])
```

Variables set via `ctx.variables` are available as `{TOKEN}` and `{BASE_URL}` in all `.hunt` files in that directory — no per-file `@var:` needed.

### Group hooks

```python
from manul_engine import before_group, after_group, GlobalContext

@before_group(tag="smoke")
def smoke_setup(ctx: GlobalContext) -> None:
    """Runs before files tagged 'smoke'."""
    ctx.variables["ENV"] = "smoke"

@after_group(tag="smoke")
def smoke_teardown(ctx: GlobalContext) -> None:
    pass
```

Place `manul_hooks.py` in the same directory as your `.hunt` files. The engine auto-discovers it.

---

## CI/CD

### GitHub Actions

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install ManulEngine
        run: |
          pip install manul-engine==0.0.9.29
          playwright install --with-deps chromium

      - name: Run tests
        run: manul --headless --html-report --screenshot on-fail tests/

      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: manul-report
          path: reports/
```

### Using the Docker image

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    container:
      image: ghcr.io/alexbeatnik/manul-engine:0.0.9.29
      options: --shm-size=1g
    steps:
      - uses: actions/checkout@v4
      - run: manul --html-report --screenshot on-fail tests/
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: manul-report
          path: reports/
```

### Reusable workflow

ManulEngine ships a reusable GitHub Actions workflow (`manul-ci.yml`) for downstream repos:

```yaml
jobs:
  e2e:
    uses: alexbeatnik/ManulEngine/.github/workflows/manul-ci.yml@main
    with:
      hunt-path: tests/
      headless: true
```

### Environment variables for CI

```bash
export MANUL_HEADLESS=true
export MANUL_BROWSER_ARGS="--no-sandbox --disable-dev-shm-usage"
export MANUL_MODEL=                  # empty = heuristics-only
```

---

## Docker

### Pre-built image

```bash
docker run --rm --shm-size=1g \
  -v $(pwd)/tests:/workspace/hunts:ro \
  -v $(pwd)/reports:/workspace/reports \
  ghcr.io/alexbeatnik/manul-engine:0.0.9.29 \
  --html-report --screenshot on-fail hunts/
```

### Image characteristics

- **Multi-stage build**: `deps` (pip + Playwright browsers) → `runtime` (slim, no build tools)
- **Non-root user**: `manul` (UID 1000) — no `--privileged` needed
- **PID 1**: `dumb-init` for proper signal handling and exit-code propagation
- **CI defaults**: `MANUL_HEADLESS=true`, `MANUL_BROWSER_ARGS="--no-sandbox --disable-dev-shm-usage"`, `TZ=UTC`
- **Build args**: `MANUL_VERSION`, `PYTHON_VERSION`, `BROWSERS` (default: `chromium`)

### Volume mounts

| Mount | Mode | Purpose |
|-------|------|---------|
| `/workspace/hunts` | `ro` | Hunt files |
| `/workspace/reports` | `rw` | HTML reports and run history |
| `/workspace/cache` | `rw` | Persistent controls cache |
| `/workspace/controls` | `ro` | Custom control Python files |
| `/workspace/scripts` | `ro` | Python helpers for `CALL PYTHON` |

### Docker Compose

The repo ships `docker-compose.yml` with two services:

```yaml
services:
  manul:
    image: ghcr.io/alexbeatnik/manul-engine:0.0.9.29
    command: --html-report --screenshot on-fail hunts/
    volumes:
      - ./tests:/workspace/hunts:ro
      - ./reports:/workspace/reports
    shm_size: '1g'

  manul-daemon:
    image: ghcr.io/alexbeatnik/manul-engine:0.0.9.29
    command: daemon hunts/ --headless
    volumes:
      - ./tests:/workspace/hunts:ro
      - ./reports:/workspace/reports
    restart: unless-stopped
    shm_size: '1g'
```

---

## Manul MCP Server

The Manul MCP Server is a separate VS Code extension that turns ManulEngine into a native MCP (Model Context Protocol) server for GitHub Copilot Chat. It allows driving a real browser session from natural language commands within VS Code.

### Installation

```bash
code --install-extension manul-engine.manul-mcp-server
```

[Marketplace](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-mcp-server) · [Open VSX](https://open-vsx.org/extension/manul-engine/manul-mcp-server) · [GitHub](https://github.com/alexbeatnik/ManulMcpServer)

### Available MCP tools

| Tool | Description |
|------|-------------|
| `manul_run_step` | Execute a single DSL step against the live browser |
| `manul_run_goal` | Execute a multi-step goal described in natural language |
| `manul_scan_page` | Scan the current page for interactive elements |
| `manul_save_hunt` | Save the current session as a `.hunt` file |
| `manul_run_hunt` | Run an existing `.hunt` file |
| `manul_run_hunt_file` | Run a hunt file by path |
| `manul_get_state` | Get current browser/page state |
| `manul_read_page_text` | Read visible text from the page |
| `manul_validate_hunt` | Validate a `.hunt` file's syntax |

### Workflow

1. Open Copilot Chat in VS Code
2. Ask Copilot to perform a browser task (e.g., "Log into saucedemo.com and add items to the cart")
3. The MCP server translates Copilot's intent into DSL steps and executes them
4. After completing the task, Copilot suggests saving the session as a `.hunt` file for replay

### Example Copilot Chat session

```
User: Navigate to saucedemo.com and log in with standard_user / secret_sauce

Copilot: I'll execute these steps using the Manul MCP Server...
  → NAVIGATE to https://www.saucedemo.com
  → VERIFY that 'Swag Labs' is present
  → FILL 'Username' with 'standard_user'
  → FILL 'Password' with 'secret_sauce'
  → CLICK the 'Login' button
  → VERIFY that 'Products' is present

All steps passed. Should I save this as a hunt file?
```

---

## Manul Engine Extension for VS Code

The companion VS Code extension provides a rich IDE experience for `.hunt` files.

### Installation

```bash
code --install-extension manul-engine.manul-engine
```

[Marketplace](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-engine) · [Open VSX](https://open-vsx.org/extension/manul-engine/manul-engine) · [GitHub](https://github.com/alexbeatnik/ManulEngineExtension)

### Features

| Feature | Description |
|---------|-------------|
| **Test Explorer** | Run and debug `.hunt` files from the Testing sidebar |
| **Syntax highlighting** | Language support for `.hunt` files |
| **Config sidebar** | Visual editor for `manul_engine_configuration.json` |
| **Cache browser** | Browse and manage the persistent controls cache |
| **Debug runner** | Gutter breakpoints, step-through with QuickPick controls |
| **Explain tooltips** | Hover over resolved steps during debug for scoring breakdown |
| **Scheduler dashboard** | Visual manager for `@schedule:` headers and run history |

### Debug workflow in VS Code

1. Open a `.hunt` file
2. Click in the gutter to set breakpoints on step lines
3. In Test Explorer, use the **Debug** run profile
4. At each breakpoint, a QuickPick menu appears with:
   - **Next Step** — advance one step
   - **Continue All** — run to the next breakpoint or end
   - **Highlight Element** — flash the resolved element on page
   - **Debug Stop** — clear all breakpoints, run to completion
   - **Stop Test** — kill the process immediately

---

## ManulAI Local Agent

Autonomous AI agent for browser automation, powered by ManulEngine. It uses LLM reasoning to plan and execute multi-step browser tasks while ManulEngine handles the deterministic element resolution.

### Installation

```bash
code --install-extension manul-engine.manulai-local-agent
```

[Marketplace](https://marketplace.visualstudio.com/items?itemName=manul-engine.manulai-local-agent) · [Open VSX](https://open-vsx.org/extension/manul-engine/manulai-local-agent) · [GitHub](https://github.com/alexbeatnik/ManulAI-local-agent)

---

## Full Ecosystem

| Component | Role | Links |
|-----------|------|-------|
| **ManulEngine** | Deterministic automation runtime (Python). Heuristic element resolver, `.hunt` DSL, CLI runner. | [PyPI](https://pypi.org/project/manul-engine/) · [GitHub](https://github.com/alexbeatnik/ManulEngine) |
| **Manul Engine Extension** | VS Code extension with debug panel, explain mode, and Test Explorer integration. | [Marketplace](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-engine) · [Open VSX](https://open-vsx.org/extension/manul-engine/manul-engine) · [GitHub](https://github.com/alexbeatnik/ManulEngineExtension) |
| **ManulMcpServer** | MCP bridge that gives Copilot Chat and other agents access to ManulEngine. | [Marketplace](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-mcp-server) · [Open VSX](https://open-vsx.org/extension/manul-engine/manul-mcp-server) · [GitHub](https://github.com/alexbeatnik/ManulMcpServer) |
| **ManulAI Local Agent** | Autonomous AI agent for browser automation, powered by ManulEngine. | [Marketplace](https://marketplace.visualstudio.com/items?itemName=manul-engine.manulai-local-agent) · [Open VSX](https://open-vsx.org/extension/manul-engine/manulai-local-agent) · [GitHub](https://github.com/alexbeatnik/ManulAI-local-agent) |
