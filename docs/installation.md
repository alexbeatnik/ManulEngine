# Installation

> **ManulEngine v0.0.9.29**

## Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.11+ | Python 3.12 also supported |
| **Playwright** | 1.58+ | Installed automatically with `manul-engine` |
| **OS** | Linux, macOS, Windows | All three platforms supported |

**Optional:**

| Tool | Purpose |
|------|---------|
| **Ollama** | Local AI self-healing fallback (not required for normal operation) |
| **VS Code** | For the companion Manul Engine Extension (Test Explorer, debug runner) |
| **Docker** | For CI/CD runner image |

## Install from PyPI

```bash
pip install manul-engine==0.0.9.29
```

Then install Playwright browsers:

```bash
playwright install
```

This installs Chromium by default. To install specific browsers:

```bash
playwright install chromium     # Chromium only (default)
playwright install firefox      # Firefox
playwright install webkit       # WebKit
```

## Virtual Environment (Recommended)

```bash
python -m venv .venv
source .venv/bin/activate       # Linux / macOS
# .venv\Scripts\activate        # Windows

pip install manul-engine==0.0.9.29
playwright install
```

## Optional: AI Self-Healing Fallback

ManulEngine works fully without AI — `"model": null` is the recommended default. If you want the optional LLM fallback for genuinely ambiguous elements:

```bash
pip install "manul-engine[ai]==0.0.9.29"
```

Then install and start Ollama:

1. Install Ollama from [ollama.com](https://ollama.com)
2. Pull a model:
   ```bash
   ollama pull qwen2.5:0.5b
   ```
3. Start the server:
   ```bash
   ollama serve
   ```

## Install from Source (Development)

```bash
git clone https://github.com/alexbeatnik/ManulEngine.git
cd ManulEngine
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
playwright install
```

Verify the installation:

```bash
python run_tests.py          # synthetic DOM test suite (no network needed)
```

## Configuration File

Create `manul_engine_configuration.json` in your project root. All keys are optional:

```json
{
  "model": null,
  "browser": "chromium",
  "controls_cache_enabled": true,
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
- Controls cache browser

## MCP Server for GitHub Copilot

A separate extension turns ManulEngine into a native MCP server for Copilot Chat:

```bash
code --install-extension manul-engine.manul-mcp-server
```

## Docker (CI/CD)

Pull the pre-built headless runner image:

```bash
docker pull ghcr.io/alexbeatnik/manul-engine:0.0.9.29
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
| Playwright browser not found | Run `playwright install` after `pip install manul-engine`. |
| Permission errors on Linux | Playwright may need system dependencies: `playwright install-deps`. |
| Ollama connection refused | Start the Ollama server: `ollama serve`. Not needed if `model` is `null`. |
