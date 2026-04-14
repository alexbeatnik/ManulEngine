# Overview

> **ManulEngine v0.0.9.29** — Deterministic, DSL-first Web & Desktop Automation Runtime

## What Is ManulEngine?

ManulEngine is an interpreter for the `.hunt` DSL — a Playwright-backed engine that runs E2E tests, RPA workflows, synthetic monitors, and AI-agent actions. It drives Chromium (and optionally Firefox or WebKit) via Playwright, resolves DOM elements with a mathematically sound `DOMScorer` (normalised 0.0–1.0 float scoring across 20+ heuristic signals and a native JavaScript `TreeWalker`), and optionally falls back to a local LLM (Ollama) as a self-healing safety net when the heuristics are genuinely ambiguous.

Everything runs **locally**. No cloud APIs, no telemetry, no external dependencies beyond Playwright.

## Architecture

```text
┌──────────────────────────────────────────────────────────┐
│                    .hunt DSL file                        │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
            ┌──────────────────┐
            │     Parser       │   parse_hunt_file() → parse_hunt_blocks()
            │   (cli.py /      │   Metadata, hooks, STEP blocks, conditionals
            │    helpers.py)   │
            └──────────┬───────┘
                       │
                       ▼
            ┌──────────────────┐
            │ Execution Engine │   run_mission() in core.py
            │  (ManulEngine)   │   Step dispatch, self-healing, retries
            └──────────┬───────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌────────────┐ ┌──────────┐ ┌──────────────┐
   │ DOMScorer  │ │ Controls │ │ Python Hooks │
   │ (scoring.  │ │ Registry │ │ [SETUP] /    │
   │  py)       │ │          │ │ CALL PYTHON  │
   └─────┬──────┘ └────┬─────┘ └──────────────┘
         │              │
         ▼              ▼
   ┌──────────────────────────┐
   │       Playwright         │   Browser interaction layer
   │  (Chromium / Firefox /   │   Async page actions
   │   WebKit / Electron)     │
   └──────────────────────────┘
```

### Core Components

| Component | File | Role |
|-----------|------|------|
| **Parser** | `cli.py`, `helpers.py` | Reads `.hunt` files, extracts metadata (`@context`, `@var`, `@tags`, `@import`), splits into STEP blocks and conditional trees |
| **Execution Engine** | `core.py` | Orchestrates step dispatch, element resolution, self-healing retries, debug pauses |
| **DOMScorer** | `scoring.py` | Normalised 0.0–1.0 heuristic scoring across five weighted channels: `cache`, `semantics`, `text`, `attributes`, `proximity` |
| **TreeWalker Snapshot** | `js_scripts.py` | JavaScript injected into each frame — walks the DOM, prunes non-interactive nodes, checks visibility |
| **Actions Mixin** | `actions.py` | Click, fill, select, hover, drag, scroll, verify, extract, explicit waits |
| **Controls Cache** | `cache.py` | Persistent per-site element resolution cache — avoids re-scoring known elements |
| **Custom Controls** | `controls.py` | `@custom_control` decorator to handle complex widgets with raw Playwright |
| **Python Hooks** | `hooks.py` | `[SETUP]` / `[TEARDOWN]` block execution, `CALL PYTHON` inline steps |
| **Lifecycle Hooks** | `lifecycle.py` | `@before_all` / `@after_all` / `@before_group` / `@after_group` global hooks |
| **Import System** | `imports.py` | `@import` / `@export` / `USE` for sharing STEP blocks across `.hunt` files |
| **Conditionals** | `conditionals.py` | `IF` / `ELIF` / `ELSE` block evaluation against live page state |
| **Reporter** | `reporter.py` | Self-contained HTML report generator (dark theme, accordions, screenshots) |
| **Scheduler** | `scheduler.py` | `@schedule:` header + `manul daemon` for recurring automation |
| **Scanner** | `scanner.py` | `manul scan <url>` — generates a draft `.hunt` file from a live page |
| **Recorder** | `recorder.py` | Semantic test recorder that captures intent, not pointer events |
| **Python API** | `api.py` | `ManulSession` — async context manager for pure-Python automation |
| **Config** | `config.py` | `EngineConfig` frozen dataclass — injectable, environment-overlay-aware |
| **LLM Provider** | `llm.py` | `OllamaProvider` / `NullProvider` — optional AI fallback |

### Companion Tools

| Tool | Description | Links |
|------|-------------|-------|
| **Manul Engine Extension** | VS Code extension — Test Explorer, syntax highlighting, config sidebar, cache browser, interactive debug runner, hover-based explain tooltips | [Marketplace](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-engine) · [Open VSX](https://open-vsx.org/extension/manul-engine/manul-engine) · [GitHub](https://github.com/alexbeatnik/ManulEngineExtension) |
| **ManulMcpServer** | MCP bridge that gives Copilot Chat and other agents access to ManulEngine | [Marketplace](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-mcp-server) · [Open VSX](https://open-vsx.org/extension/manul-engine/manul-mcp-server) · [GitHub](https://github.com/alexbeatnik/ManulMcpServer) |
| **ManulAI Local Agent** | Autonomous AI agent for browser automation, powered by ManulEngine | [Marketplace](https://marketplace.visualstudio.com/items?itemName=manul-engine.manulai-local-agent) · [Open VSX](https://open-vsx.org/extension/manul-engine/manulai-local-agent) · [GitHub](https://github.com/alexbeatnik/ManulAI-local-agent) |
| **Docker CI Runner** | `ghcr.io/alexbeatnik/manul-engine` — headless CI image with `dumb-init`, non-root user, baked-in defaults | — |

## Philosophy

### Local-First

ManulEngine runs entirely on your machine. Element resolution is done by local heuristic scoring. No internet connection is needed beyond what your test targets require. The optional AI fallback uses Ollama — a local model runner — never a cloud API.

### Determinism Over Prompt Variance

The primary resolver is not an LLM. It is a weighted heuristic scorer backed by a native JavaScript `TreeWalker`. Same page state plus same step text equals the same resolution — no prompt variance, no non-deterministic cloud dependency.

### Transparency and Explainability

When `--explain` is enabled, every resolved step prints a per-channel breakdown:

```text
┌─ EXPLAIN: Target = "Login"
│  Step: Click the 'Login' button
│
│  #1 <button> "Login"
│     total:      0.593
│     text:       0.281
│     attributes: 0.050
│     semantics:  0.225
│     proximity:  0.037
│     cache:      0.000
│
└─ Decision: selected "Login" with score 0.593
```

When a step fails, you get the scoring data to diagnose exactly why.

### Dual-Persona Workflow

Manual QA writes plain-English `.hunt` steps — no code required. SDETs extend the same files with Python hooks, lifecycle orchestration, and custom control handlers for complex widgets. Both personas work on the same artifact.

### Optional AI, Off by Default

`"model": null` is the recommended default. The engine is not AI-powered — it is heuristics-first with an optional local AI safety net for genuinely ambiguous elements.

## Four Automation Pillars

The same runtime and the same DSL serve four use cases:

| Pillar | How |
|--------|-----|
| **QA / E2E Testing** | Write plain-English flows, verify outcomes, attach HTML reports and screenshots. No selectors in the test source. |
| **RPA Workflows** | Log into portals, fill forms, extract values, hand off to Python for backend or filesystem steps. |
| **Synthetic Monitoring** | Pair `.hunt` files with `@schedule:` and `manul daemon` for recurring health checks. |
| **AI Agent Targets** | Constrained DSL execution is safer than raw Playwright for external agents — the runtime still owns scoring, retries, and validation. |

## Project Status

ManulEngine is **alpha-stage** and solo-developed. It is actively battle-tested against adversarial DOM fixtures and real-world sites, but:

- Bugs are expected
- APIs may evolve
- There are no promises about stability or production readiness

The core claim is **transparency**: when a step works, you can see exactly why; when it fails, you get the scoring breakdown to diagnose it.
