import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";

// ── Default configuration values ─────────────────────────────────────────────

const DEFAULT_CONFIG = {
  _note:
    "ManulEngine configuration. All keys are optional. Env vars MANUL_* always override.",
  model: null,
  headless: false,
  browser: "chromium",
  browser_args: [],
  timeout: 5000,
  nav_timeout: 30000,
  ai_always: false,
  ai_policy: "prior",
  ai_threshold: null,
  controls_cache_enabled: true,
  controls_cache_dir: "cache",
  log_name_maxlen: 0,
  log_thought_maxlen: 0,
  workers: 1,
};

// ── WebviewViewProvider ───────────────────────────────────────────────────────

export class ConfigPanelProvider implements vscode.WebviewViewProvider {
  public static readonly viewId = "manul.configView";

  private _view?: vscode.WebviewView;
  private readonly _workspaceRoot: string;

  constructor(private readonly _context: vscode.ExtensionContext) {
    const folders = vscode.workspace.workspaceFolders;
    this._workspaceRoot = folders?.[0]?.uri.fsPath ?? process.cwd();
  }

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this._view = webviewView;
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = this._getHtml(webviewView.webview);

    // Handle messages from the webview
    webviewView.webview.onDidReceiveMessage(
      async (msg: { command: string; config?: Record<string, unknown> }) => {
        switch (msg.command) {
          case "load":
            webviewView.webview.postMessage({
              command: "config",
              config: this._readConfig(),
              exists: this._configExists(),
              promptsExist: this._promptsExist(),
            });
            break;

          case "save":
            if (msg.config) {
              this._writeConfig(msg.config);
              vscode.window.showInformationMessage(
                "ManulEngine: configuration saved."
              );
            }
            break;

          case "generate":
            this._writeConfig(DEFAULT_CONFIG);
            webviewView.webview.postMessage({
              command: "config",
              config: this._readConfig(),
              exists: true,
            });
            vscode.window.showInformationMessage(
              "ManulEngine: default configuration file created."
            );
            break;

          case "open":
            vscode.workspace
              .openTextDocument(this._configPath())
              .then((doc) => vscode.window.showTextDocument(doc));
            break;

          case "addPrompts": {
            const destDir = path.join(this._workspaceRoot, "prompts");
            if (fs.existsSync(destDir)) {
              vscode.window.showWarningMessage(
                "ManulEngine: prompts/ folder already exists in workspace."
              );
              webviewView.webview.postMessage({ command: "promptsExist", exists: true });
              break;
            }
            const srcDir = path.join(this._context.extensionPath, "prompts");
            fs.mkdirSync(destDir, { recursive: true });
            for (const file of fs.readdirSync(srcDir)) {
              fs.copyFileSync(path.join(srcDir, file), path.join(destDir, file));
            }
            vscode.window.showInformationMessage(
              "ManulEngine: default prompts added to prompts/ folder."
            );
            webviewView.webview.postMessage({ command: "promptsExist", exists: true });
            break;
          }
        }
      },
      undefined,
      this._context.subscriptions
    );
  }

  private _configPath(): string {
    const name = vscode.workspace
      .getConfiguration("manulEngine")
      .get<string>("configFile", "manul_engine_configuration.json");
    return path.join(this._workspaceRoot, name);
  }

  private _configExists(): boolean {
    return fs.existsSync(this._configPath());
  }

  private _promptsExist(): boolean {
    return fs.existsSync(path.join(this._workspaceRoot, "prompts"));
  }

  private _readConfig(): Record<string, unknown> {
    try {
      const raw = fs.readFileSync(this._configPath(), "utf-8");
      return JSON.parse(raw) as Record<string, unknown>;
    } catch {
      return { ...DEFAULT_CONFIG };
    }
  }

  private _writeConfig(config: Record<string, unknown>): void {
    const p = this._configPath();
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, JSON.stringify(config, null, 2) + "\n", "utf-8");
  }

  private _getHtml(webview: vscode.Webview): string {
    const nonce = Math.random().toString(36).slice(2);
    return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta http-equiv="Content-Security-Policy"
    content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}'; connect-src http://localhost:11434;"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>ManulEngine Config</title>
  <style>
    body { font-family: var(--vscode-font-family); font-size: var(--vscode-font-size);
           color: var(--vscode-foreground); padding: 10px; }
    h2 { font-size: 1.1em; margin-bottom: 8px; }
    label { display: block; margin-top: 10px; font-weight: bold; font-size: 0.95em; }
    input[type=text], input[type=number], select {
      width: 100%; box-sizing: border-box; padding: 4px 6px;
      background: var(--vscode-input-background);
      color: var(--vscode-input-foreground);
      border: 1px solid var(--vscode-input-border, #444); border-radius: 3px;
      font-size: 1em; }
    input[type=checkbox] { margin-top: 6px; }
    .checkbox-row { display: flex; align-items: center; gap: 8px; margin-top: 10px; }
    .checkbox-row label { margin-top: 0; }
    .hint { font-size: 0.85em; color: var(--vscode-descriptionForeground); margin-top: 2px; }
    .btn-row { display: flex; gap: 8px; margin-top: 16px; flex-wrap: wrap; }
    button {
      padding: 5px 12px; border: none; border-radius: 3px; cursor: pointer;
      background: var(--vscode-button-background);
      color: var(--vscode-button-foreground); font-size: 0.95em; }
    button.secondary {
      background: var(--vscode-button-secondaryBackground);
      color: var(--vscode-button-secondaryForeground); }
    #no-config { display: none; margin-bottom: 12px; padding: 8px;
      background: var(--vscode-editorWarning-background, #3a3000);
      border-left: 3px solid var(--vscode-editorWarning-foreground, #cca700);
      font-size: 0.92em; }
    #model-wrap { position: relative; }
    #model { width: 100%; box-sizing: border-box; padding: 4px 6px;
      background: var(--vscode-input-background); color: var(--vscode-input-foreground);
      border: 1px solid var(--vscode-input-border, #444); border-radius: 3px; font-size: 1em; }
    #ollama-status { display: flex; align-items: center; gap: 5px; margin-top: 3px; font-size: 0.85em;
      color: var(--vscode-descriptionForeground); }
    .dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
    .dot.ok  { background: #4ec94e; }
    .dot.off { background: #888; }
    .dot.spin { background: #888; animation: pulse 1s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
  </style>
</head>
<body>
  <div id="no-config">
    ⚠️ No <code>manul_engine_configuration.json</code> found in workspace root.
    <div class="btn-row" style="margin-top:8px">
      <button id="btn-generate">Generate Default Config</button>
    </div>
  </div>

  <div id="form">
    <label>model</label>
    <div id="model-wrap">
      <input id="model" list="ollama-models" autocomplete="off"
             placeholder="empty = heuristics-only (null)"/>
      <datalist id="ollama-models"></datalist>
    </div>
    <div id="ollama-status"><span class="dot spin" id="ollama-dot"></span><span id="ollama-label">Checking Ollama…</span></div>
    <div class="hint">Select from installed Ollama models, or type any model name. Leave empty to disable AI.</div>

    <div class="checkbox-row">
      <input type="checkbox" id="headless"/>
      <label for="headless">headless</label>
    </div>
    <div class="hint">Run browser in headless mode.</div>

    <label>browser
      <select id="browser">
        <option value="chromium">Chromium (default)</option>
        <option value="firefox">Firefox</option>
        <option value="webkit">WebKit (Safari)</option>
      </select>
    </label>
    <div class="hint">Browser engine used by Playwright to run hunt tests.</div>

    <label>browser_args
      <input type="text" id="browser_args" placeholder="e.g. --disable-gpu, --lang=uk"/>
    </label>
    <div class="hint">Extra launch flags passed to the browser, comma-separated. Chromium always gets --no-sandbox --start-maximized.</div>

    <label>timeout (ms)
      <input type="number" id="timeout" min="500" step="500"/>
    </label>
    <div class="hint">Default action timeout.</div>

    <label>nav_timeout (ms)
      <input type="number" id="nav_timeout" min="1000" step="1000"/>
    </label>
    <div class="hint">Navigation timeout.</div>

    <div class="checkbox-row">
      <input type="checkbox" id="ai_always"/>
      <label for="ai_always">ai_always</label>
    </div>
    <div class="hint" id="ai-always-hint">Always call the LLM picker (bypasses heuristic short-circuits). Has no effect when model is empty.</div>

    <label>ai_policy
      <select id="ai_policy">
        <option value="prior">prior (heuristic score as hint)</option>
        <option value="strict">strict (force max-score element)</option>
      </select>
    </label>

    <label>ai_threshold
      <input type="number" id="ai_threshold" placeholder="null = auto-derive from model size"/>
    </label>
    <div class="hint">Score threshold before LLM fallback. Empty = auto.</div>

    <div class="checkbox-row">
      <input type="checkbox" id="controls_cache_enabled"/>
      <label for="controls_cache_enabled">controls_cache_enabled</label>
    </div>

    <label>controls_cache_dir
      <input type="text" id="controls_cache_dir" placeholder="cache"/>
    </label>
    <div class="hint">Directory for cache files (relative to CWD or absolute).</div>

    <label>log_name_maxlen
      <input type="number" id="log_name_maxlen" min="0"/>
    </label>
    <div class="hint">Truncate element names in logs (0 = no limit).</div>

    <label>log_thought_maxlen
      <input type="number" id="log_thought_maxlen" min="0"/>
    </label>
    <div class="hint">Truncate LLM thought strings in logs (0 = no limit).</div>

    <label>workers
      <select id="workers">
        <option value="1">1 (sequential, default)</option>
        <option value="2">2</option>
        <option value="3">3</option>
        <option value="4">4</option>
      </select>
    </label>
    <div class="hint">Max hunt files to run in parallel. Each worker spawns a separate browser process.</div>

    <div class="btn-row">
      <button id="btn-save">💾 Save</button>
      <button id="btn-open" class="secondary">Open in Editor</button>
    </div>

    <div class="btn-row" style="margin-top:20px;border-top:1px solid var(--vscode-widget-border,#444);padding-top:14px">
      <button id="btn-add-prompts" class="secondary">Add Default Prompts</button>
    </div>
    <div class="hint">Copies LLM prompt templates (html_to_hunt.md, description_to_hunt.md) into a <code>prompts/</code> folder in your workspace. Disabled if the folder already exists.</div>
  </div>

  <script nonce="${nonce}">
    const vsc = acquireVsCodeApi();

    function g(id) { return document.getElementById(id); }

    function doGenerate() { vsc.postMessage({ command: 'generate' }); }
    function doOpen()     { vsc.postMessage({ command: 'open' }); }

    function doSave() {
      const modelVal  = g('model').value.trim();
      const threshVal = g('ai_threshold').value.trim();
      const cfg = {
        model: modelVal === '' ? null : modelVal,
        headless: g('headless').checked,
        browser: g('browser').value,
        browser_args: g('browser_args').value.trim().split(/[,\s]+/).map(s => s.trim()).filter(Boolean),
        timeout: parseInt(g('timeout').value, 10) || 5000,
        nav_timeout: parseInt(g('nav_timeout').value, 10) || 30000,
        ai_always: modelVal !== '' && g('ai_always').checked,
        ai_policy: g('ai_policy').value,
        ai_threshold: threshVal === '' ? null : parseInt(threshVal, 10),
        controls_cache_enabled: g('controls_cache_enabled').checked,
        controls_cache_dir: g('controls_cache_dir').value.trim() || 'cache',
        log_name_maxlen: (v => isNaN(v) ? 0 : v)(parseInt(g('log_name_maxlen').value, 10)),
        log_thought_maxlen: (v => isNaN(v) ? 0 : v)(parseInt(g('log_thought_maxlen').value, 10)),
        workers: parseInt(g('workers').value, 10) || 1,
      };
      vsc.postMessage({ command: 'save', config: cfg });
    }

    function doLoad(config, exists) {
      g('no-config').style.display = exists ? 'none' : 'block';
      g('model').value         = config.model ?? '';
      g('headless').checked    = !!config.headless;
      const _validBrowsers = ['chromium', 'firefox', 'webkit'];
      g('browser').value       = _validBrowsers.includes(config.browser) ? config.browser : 'chromium';
      g('browser_args').value  = Array.isArray(config.browser_args) ? config.browser_args.join(', ') : '';
      g('timeout').value       = config.timeout ?? 5000;
      g('nav_timeout').value   = config.nav_timeout ?? 30000;
      g('ai_always').checked   = !!config.ai_always;
      g('ai_policy').value     = config.ai_policy ?? 'prior';
      g('ai_threshold').value  = config.ai_threshold ?? '';
      g('controls_cache_enabled').checked = config.controls_cache_enabled !== false;
      g('controls_cache_dir').value       = config.controls_cache_dir ?? 'cache';
      g('log_name_maxlen').value          = config.log_name_maxlen ?? 0;
      g('log_thought_maxlen').value       = config.log_thought_maxlen ?? 0;
      const _w = Math.min(4, Math.max(1, parseInt(String(config.workers ?? 1), 10)));
      g('workers').value                  = String(isNaN(_w) ? 1 : _w);
      syncAiAlways();
    }

    function doAddPrompts() { vsc.postMessage({ command: 'addPrompts' }); }
    g('btn-generate').addEventListener('click', doGenerate);
    g('btn-save').addEventListener('click', doSave);
    g('btn-open').addEventListener('click', doOpen);
    g('btn-add-prompts').addEventListener('click', doAddPrompts);

    // Disable ai_always when no model is set
    function syncAiAlways() {
      const hasModel = g('model').value.trim() !== '';
      g('ai_always').disabled = !hasModel;
      g('ai-always-hint').style.color = hasModel
        ? '' : 'var(--vscode-editorWarning-foreground, #cca700)';
      if (!hasModel) { g('ai_always').checked = false; }
    }
    g('model').addEventListener('input', syncAiAlways);
    g('model').addEventListener('change', syncAiAlways);

    function syncPromptsBtn(exists) {
      const btn = g('btn-add-prompts');
      btn.disabled = !!exists;
      btn.title = exists ? 'prompts/ folder already exists in workspace' : '';
    }
    window.addEventListener('message', function(event) {
      const msg = event.data;
      if (msg.command === 'config') {
        doLoad(msg.config, msg.exists);
        syncPromptsBtn(msg.promptsExist);
      }
      if (msg.command === 'promptsExist') { syncPromptsBtn(msg.exists); }
    });

    // ── Ollama model discovery ────────────────────────────────────────────────
    (function fetchOllamaModels() {
      const dot   = g('ollama-dot');
      const label = g('ollama-label');
      const dl    = g('ollama-models');

      function buildDatalist(models) {
        dl.textContent = ''; // safe DOM clear (no innerHTML)
        var nullOpt = document.createElement('option');
        nullOpt.value = '';
        nullOpt.textContent = 'null (heuristics-only)';
        dl.appendChild(nullOpt);
        models.forEach(function(n) {
          var opt = document.createElement('option');
          opt.value = String(n);
          opt.textContent = String(n);
          dl.appendChild(opt);
        });
      }

      fetch('http://localhost:11434/api/tags', { signal: AbortSignal.timeout(3000) })
        .then(function(r) { return r.json(); })
        .then(function(data) {
          const models = (data.models || []).map(function(m) { return m.name; });
          buildDatalist(models);
          dot.className = 'dot ok';
          label.textContent = 'Ollama connected — ' + models.length + ' model' + (models.length !== 1 ? 's' : '') + ' available';
        })
        .catch(function() {
          buildDatalist([]);
          dot.className = 'dot off';
          label.textContent = 'Ollama not available — type model name manually or leave empty';
        });
    })();

    vsc.postMessage({ command: 'load' });
  </script>
</body>
</html>`;
  }
}

/** Command: generate default config file. */
export function generateConfigCommand(): void {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) {
    vscode.window.showWarningMessage("No workspace folder open.");
    return;
  }
  const configPath = path.join(
    folders[0].uri.fsPath,
    "manul_engine_configuration.json"
  );
  if (fs.existsSync(configPath)) {
    vscode.window
      .showWarningMessage(
        "manul_engine_configuration.json already exists. Overwrite?",
        "Yes",
        "No"
      )
      .then((choice) => {
        if (choice === "Yes") {
          writeDefault(configPath);
        }
      });
    return;
  }
  writeDefault(configPath);
}

function writeDefault(configPath: string): void {
  fs.writeFileSync(
    configPath,
    JSON.stringify(DEFAULT_CONFIG, null, 2) + "\n",
    "utf-8"
  );
  vscode.workspace
    .openTextDocument(configPath)
    .then((doc) => vscode.window.showTextDocument(doc));
  vscode.window.showInformationMessage(
    "ManulEngine: default configuration generated."
  );
}
