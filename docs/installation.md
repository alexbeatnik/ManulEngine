# Installation

> **ManulEngine 0.1.0**

## Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.11+ | Python 3.12 also supported |
| **Google Chrome / Chromium** | any recent | Must be on `PATH` (or set `channel` / `executable_path`) — the engine drives it directly over CDP |
| **OS** | Linux, macOS, Windows | All three platforms supported |

No Playwright, no Node.js, no bundled browser download — the only runtime dependency is `websockets`.

**Optional:**

| Tool | Purpose |
|------|---------|
| **VS Code** | For the companion Manul Engine Extension (Test Explorer, debug runner) |
| **Docker** | For the CI/CD runner image |

## Install from PyPI

```bash
pip install manul-engine==0.1.0
# Requires a system-installed Google Chrome / Chromium on PATH.
```

## Virtual Environment (Recommended)

```bash
python -m venv .venv
source .venv/bin/activate       # Linux / macOS
# .venv\Scripts\activate        # Windows

pip install manul-engine==0.1.0
```

## Install from Source (Development)

```bash
git clone https://github.com/alexbeatnik/ManulEngine.git
cd ManulEngine
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# Requires a system Google Chrome / Chromium on PATH (the CDP target).
```

Verify the installation:

```bash
python run_tests.py          # synthetic DOM test suite (no network needed)
```

## Configuration File

Create `manul_engine_configuration.json` in your project root. All keys are optional:

```json
{
  "browser": "chromium",
  "semantic_cache_enabled": true
}
```

This is the minimal recommended configuration — fully heuristics-only, no AI dependency.

See [DSL Syntax Reference → Configuration](dsl-syntax.md#configuration-reference) for the full key table.

## VS Code Extension

Install the companion Manul Engine Extension for VS Code from the Marketplace:

```bash
code --install-extension manul-engine.manul-engine
```

Or search for **"Manul Engine"** in the VS Code Extensions sidebar.

The extension provides:
- Test Explorer integration (run/debug `.hunt` files from the sidebar)
- Syntax highlighting for `.hunt` files
- Config sidebar for `manul_engine_configuration.json`
- Interactive debug runner with gutter breakpoints
- Hover-based explain tooltips during debug pauses

It also supports the Go engine ([ManulEngineGo](https://github.com/alexbeatnik/ManulEngineGo)) out of the box — the runtime is auto-detected from the workspace.

## MCP Server for GitHub Copilot

A separate extension turns ManulEngine into a native MCP server for Copilot Chat:

```bash
code --install-extension manul-engine.manul-mcp-server
```

## Docker (CI/CD)

Pull the pre-built headless runner image (system Chrome baked in):

```bash
docker pull ghcr.io/alexbeatnik/manul-engine:0.1.0
```

Or use the provided `Dockerfile` for custom builds. See [Integration → Docker](integration.md#docker) for usage details.

## Verifying the Installation

```bash
# Check the CLI is available
manul --help

# Run a quick smoke test
echo '@context: Quick test
@title: Smoke

STEP 1: Open example.com
    NAVIGATE to https://example.com
    VERIFY that "Example Domain" is present

DONE.' > smoke.hunt

manul smoke.hunt
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `manul: command not found` | Ensure `pip install` was run in the active venv. Try `python -m manul_engine` as a fallback. |
| Chrome/Chromium not found | Install Google Chrome or Chromium and ensure it is on `PATH` (or set `executable_path` / `MANUL_CHANNEL`). |
| Sandbox errors on Linux/CI | Add `--no-sandbox` via `MANUL_BROWSER_ARGS` (already set in the Docker image). |
