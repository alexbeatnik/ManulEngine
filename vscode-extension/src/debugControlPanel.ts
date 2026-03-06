/**
 * debugControlPanel.ts — Floating QuickPick overlay for ManulEngine debug control.
 *
 * Uses vscode.window.createQuickPick() (low-level API) so the picker can be
 * dismissed programmatically via abort() when the user clicks Stop in Test Explorer.
 *
 * Buttons:  ⏭ Next Step  |  ▶ Continue All
 * ESC / Stop → abort() hides the picker → treated as "next" so Python unblocks.
 *
 * Window raising (Linux): spawns xdotool / wmctrl + notify-send (both silent-fail).
 */
import * as vscode from "vscode";
import { exec } from "child_process";

export type PauseChoice = "next" | "continue";

const NEXT_LABEL = "⏭  Next Step";
const CONT_LABEL = "▶  Continue All";

/** Best-effort: raise the VS Code window above other apps on Linux. */
function tryRaiseWindow(stepIdx: number, stepText: string): void {
  if (process.platform !== "linux") { return; }
  // X11: xdotool activates by WM_CLASS, fallback wmctrl by title.
  exec(
    'xdotool search --onlyvisible --class "Code" windowactivate 2>/dev/null || wmctrl -a "Visual Studio Code" 2>/dev/null || true',
    () => { /* ignore errors */ }
  );
  // OS notification flashes taskbar on both X11 and Wayland.
  const safe = stepText.replace(/'/g, "'").slice(0, 80);
  exec(
    `notify-send -u normal -t 5000 '🐛 ManulEngine Debug — Step ${stepIdx}' '${safe}' 2>/dev/null || true`,
    () => { /* ignore errors */ }
  );
}

export class DebugControlPanel {
  private static _instance: DebugControlPanel | undefined;
  private _activeQp: vscode.QuickPick<vscode.QuickPickItem> | undefined;

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
      qp.items = [{ label: NEXT_LABEL }, { label: CONT_LABEL }];
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
        done(label === CONT_LABEL ? "continue" : "next");
      });

      // ESC or programmatic hide → treat as "next" so Python readline() unblocks.
      qp.onDidHide(() => done("next"));

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

  /** Reset singleton so next run gets a fresh instance. */
  dispose(): void {
    this._activeQp?.hide();
    DebugControlPanel._instance = undefined;
  }
}

