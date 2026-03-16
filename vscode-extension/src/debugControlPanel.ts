/**
 * debugControlPanel.ts — Floating QuickPick overlay for ManulEngine debug control.
 *
 * Uses vscode.window.createQuickPick() (low-level API) so the picker can be
 * dismissed programmatically via abort() when the user clicks Stop in Test Explorer.
 *
 * Buttons:  ⏭ Next Step  |  ▶ Continue All  |  👁 Highlight Element
 * ESC / Stop → abort() hides the picker → treated as "next" so Python unblocks.
 *
 * Window raising (Linux): spawns xdotool / wmctrl + notify-send (both silent-fail).
 */
import * as vscode from "vscode";
import { exec, execFile } from "child_process";

export type PauseChoice = "next" | "continue" | "highlight" | "explain" | "debug-stop" | "stop-test";

const NEXT_LABEL  = "⏭  Next Step";
const CONT_LABEL  = "▶  Continue All";
const HIGH_LABEL  = "👁  Highlight Element";
const EXPL_LABEL  = "💡  Explain Step";
const DSTOP_LABEL = "⏹  Debug Stop";
const SSTOP_LABEL = "🛑  Stop Test";

/** Best-effort: raise the VS Code window above other apps on Linux. */
function tryRaiseWindow(stepIdx: number, stepText: string): void {
  if (process.platform !== "linux") { return; }
  // X11: xdotool activates by WM_CLASS, fallback wmctrl by title.
  exec(
    'xdotool search --onlyvisible --class "Code" windowactivate 2>/dev/null || wmctrl -a "Visual Studio Code" 2>/dev/null || true',
    () => { /* ignore errors */ }
  );
  // OS notification flashes taskbar on both X11 and Wayland.
  // Use execFile (argv array) instead of exec() to avoid shell-injection from
  // crafted .hunt step text that could break out of the notify-send quotes.
  const safeText = stepText.slice(0, 80);
  execFile(
    "notify-send",
    ["-u", "normal", "-t", "5000", `🐛 ManulEngine Debug — Step ${stepIdx}`, safeText],
    () => { /* ignore errors — notify-send may not be installed */ }
  );
}

export class DebugControlPanel {
  private static _instance: DebugControlPanel | undefined;
  private _activeQp: vscode.QuickPick<vscode.QuickPickItem> | undefined;
  /** When true, the next onDidHide resolves with "explain" instead of "next". */
  private _explainOnHide = false;

  private constructor(
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    private readonly _ctx: vscode.ExtensionContext
  ) {}

  static getInstance(ctx: vscode.ExtensionContext): DebugControlPanel {
    if (!DebugControlPanel._instance) {
      DebugControlPanel._instance = new DebugControlPanel(ctx);
    }
    return DebugControlPanel._instance;
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  /**
   * Show a floating QuickPick overlay for the current debug step.
   * ignoreFocusOut=true keeps it visible even when the browser is active.
   * Calling abort() (e.g. from Stop button) hides it immediately.
   */
  showPause(step: string, idx: number): Promise<PauseChoice> {
    // Raise OS window and show system notification (fires async, best-effort).
    tryRaiseWindow(idx, step);

    return new Promise<PauseChoice>((resolve) => {
      const qp = vscode.window.createQuickPick<vscode.QuickPickItem>();
      this._activeQp = qp;

      qp.title = `🐛 ManulEngine Debug — Step ${idx}`;
      qp.placeholder = step.length > 120 ? step.slice(0, 120) + "…" : step;
      qp.items = [
        { label: NEXT_LABEL },
        { label: CONT_LABEL },
        { label: HIGH_LABEL,  description: "Scroll the browser to the highlighted element" },
        { label: EXPL_LABEL,  description: "Show heuristic score breakdown for this step" },
        { label: DSTOP_LABEL, description: "Skip all remaining breakpoints and run to end" },
        { label: SSTOP_LABEL, description: "Abort the test immediately" },
      ];
      qp.ignoreFocusOut = true;

      let resolved = false;
      const done = (choice: PauseChoice) => {
        if (resolved) { return; }
        resolved = true;
        this._activeQp = undefined;
        qp.dispose();
        resolve(choice);
      };

      qp.onDidAccept(() => {
        const label = qp.selectedItems[0]?.label;
        if (label === HIGH_LABEL) {
          done("highlight");
        } else if (label === EXPL_LABEL) {
          done("explain");
        } else if (label === DSTOP_LABEL) {
          done("debug-stop");
        } else if (label === SSTOP_LABEL) {
          done("stop-test");
        } else {
          done(label === CONT_LABEL ? "continue" : "next");
        }
      });

      // ESC or programmatic hide → resolve with "next" (or "explain" if
      // triggerExplain() fired) so Python readline() unblocks.
      qp.onDidHide(() => {
        const choice: PauseChoice = this._explainOnHide ? "explain" : "next";
        this._explainOnHide = false;
        done(choice);
      });

      qp.show();
    });
  }

  /**
   * Programmatically close the active QuickPick (e.g. when Stop is pressed).
   * The pending showPause() promise resolves with "next" via onDidHide,
   * which unblocks Python's stdin readline and lets the process exit cleanly.
   */
  abort(): void {
    this._activeQp?.hide();
  }

  /**
   * Programmatically trigger "explain" from an external command.
   * Hides the QuickPick so the pending showPause() promise resolves with
   * "explain", which is sent to Python's stdin to print scoring data.
   */
  triggerExplain(): void {
    if (!this._activeQp) { return; }
    this._explainOnHide = true;
    this._activeQp.hide();
  }

  /** Reset singleton so next run gets a fresh instance. */
  dispose(): void {
    this._activeQp?.hide();
    DebugControlPanel._instance = undefined;
  }
}

