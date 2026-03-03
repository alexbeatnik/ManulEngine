# ManulEngine — VS Code Extension

> Hunt file language support, one-click test runner, configuration UI, and cache browser for [ManulEngine](https://github.com/alexbeatnik/ManulEngine) browser automation.

[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/manul-engine.manul-engine?label=VS%20Code%20Marketplace&logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-engine)
[![PyPI](https://img.shields.io/pypi/v/manul-engine?label=PyPI&logo=pypi)](https://pypi.org/project/manul-engine/)

---

## Features

### 🎨 Hunt File Language Support
- Syntax highlighting for `.hunt` files
- Comment toggling (`#`)
- Bracket/quote matching and auto-closing
- File icon in the explorer

### ▶️ Run Hunt Files
Three ways to run a `.hunt` file:

| Method | How |
|--------|-----|
| **Editor title button** | Click the `▶` icon in the top-right of the editor when a `.hunt` file is open |
| **Explorer context menu** | Right-click a `.hunt` file → *ManulEngine: Run Hunt File* |
| **Terminal mode** | Right-click → *ManulEngine: Run Hunt File in Terminal* (runs raw in the integrated terminal) |

Output streams live into a dedicated **ManulEngine** output channel. ✅ / ❌ status is appended on completion.

### 🧪 Test Explorer Integration
Hunt files appear in the **VS Code Test Explorer** as top-level test items (one per file). When a hunt is run via Test Explorer:
- Each numbered step is shown as a child item with pass/fail status
- Failed steps display the engine output as the failure message
- Steps that were never reached are marked as skipped
- The step tree is cleared after the run so the explorer shows the correct file-level count

### ⚙️ Configuration Panel
An interactive sidebar panel for editing `manul_engine_configuration.json` without touching the file directly.

- **Model** — Ollama model name (leave blank for heuristics-only mode)
- **AI Policy** — `prior` (heuristic as hint) or `strict`
- **AI Threshold** — score cutoff before LLM fallback (`null` = auto)
- **AI Always** — always call the LLM picker (automatically disabled when no model is set)
- **Browser** — browser engine: Chromium, Firefox, or WebKit
- **Browser Args** — extra launch flags for the browser (comma-separated)
- **Headless** — run browser headless
- **Timeouts** — action and navigation timeouts in ms
- **Controls Cache** — enable/disable and set the cache directory
- **Log truncation** — max length for element names and LLM thoughts in logs
- **Ollama status indicator** — live dot showing whether Ollama is reachable at `localhost:11434`, with model autocomplete from the running instance

Changes are saved to `manul_engine_configuration.json` at the workspace root. A *Generate Default Config* button creates the file if it doesn't exist yet.

### 🗂️ Cache Browser
The **Cache** sidebar tree shows per-site cache entries created by ManulEngine's persistent controls cache. You can:
- Browse sites and their cached page entries
- Clear the cache for a specific site (trash icon on hover)
- Clear all cache entries at once (toolbar button)
- Refresh the tree manually

---

## Requirements

- **ManulEngine** installed in the workspace or globally:
  ```bash
  pip install manul-engine          # global / user
  # or in a project venv:
  pip install -e .
  ```
- **Python 3.11+**
- **Playwright** browsers (installed by ManulEngine's setup)
- **Ollama** (optional) — only needed for AI-assisted element picking

---

## Auto-detection of the `manul` executable

The extension probes the following locations in order (platform-aware):

1. Custom path from **`manulEngine.manulPath`** setting (if set and exists)
2. `.venv/bin/manul` in the workspace root (also checks `venv/`, `env/`, `.env/`)
3. `~/.local/bin/manul` (pip --user, Linux/macOS)
4. `~/Library/Python/*/bin/manul` (pip --user, macOS)
5. `~/.local/pipx/venvs/manul-engine/bin/manul` (pipx)
6. `/opt/homebrew/bin/manul` (Homebrew, Apple Silicon)
7. `/usr/local/bin/manul`, `/usr/bin/manul` (system-wide)
8. Shell login init lookup (`$SHELL -lc 'command -v manul'`) — sources fish/zsh/bash/pyenv/conda init so shims are found
9. Windows: `%APPDATA%\Python\*\Scripts\manul.exe`, `%LOCALAPPDATA%\Programs\Python\*\Scripts\manul.exe`

---

## Extension Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `manulEngine.manulPath` | `""` | Absolute path to the `manul` CLI. Leave empty to auto-detect. |
| `manulEngine.configFile` | `manul_engine_configuration.json` | Config file name resolved from the workspace root. |

---

## Getting Started

1. Install ManulEngine:
   ```bash
   pip install manul-engine
   playwright install chromium
   ```

2. Open your project folder in VS Code. The extension activates automatically when a `.hunt` file is present.

3. Run `ManulEngine: Generate Default Config` from the Command Palette to create `manul_engine_configuration.json`.

4. Open the **ManulEngine** activity bar panel to configure Ollama and cache settings.

5. Open or create a `.hunt` file and click ▶ to run it.

---

## Example Hunt File

```hunt
@context: Login and verify dashboard
@blueprint: smoke_login

1. NAVIGATE to https://example.com/login
2. Fill 'Email' field with 'user@example.com'
3. Fill 'Password' field with 'secret'
4. Click the 'Sign In' button
5. VERIFY that 'Welcome' is present.
6. DONE.
```

See the [ManulEngine README](https://github.com/alexbeatnik/ManulEngine) for the full step reference.

---

## Release Notes

### 0.0.54
- Executable auto-detection now checks `venv/`, `env/`, and `.env/` in addition to `.venv/` — fixes `spawn manul ENOENT` for projects that use a non-dotted venv folder name

### 0.0.53
- Hunt file syntax highlighting, Test Explorer integration, configuration panel, cache browser
- Smart `manul` executable auto-detection across pip, pipx, Homebrew, pyenv, conda, and custom paths
- Per-file workspace root resolution for multi-root workspaces
- PowerShell-aware terminal command (`&` prefix)
- Shell-specific login flags (bash/zsh vs fish vs sh/dash)
- Fallback cache eviction on transient shell lookup failures
- Font size improvements in the configuration panel
- Browser selection (`chromium`, `firefox`, `webkit`) in the configuration panel
- Browser args field for passing extra launch flags to the browser
