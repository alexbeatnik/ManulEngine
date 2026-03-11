/**
 * Shared constants used across the ManulEngine VS Code extension.
 */

import * as vscode from "vscode";

/** Default configuration file name. User-configurable via `manulEngine.configFile` setting. */
export const DEFAULT_CONFIG_FILENAME = "manul_engine_configuration.json";

/** Debug pause protocol marker emitted by the Python engine on stdout. */
export const PAUSE_MARKER = "\x00MANUL_DEBUG_PAUSE\x00";

/** Terminal name for normal (non-debug) hunt runs. */
export const TERMINAL_NAME = "ManulEngine";

/** Terminal name for interactive debug runs. */
export const DEBUG_TERMINAL_NAME = "ManulEngine Debug";

/**
 * Read the effective config file name from VS Code settings,
 * falling back to the default.
 */
export function getConfigFileName(): string {
  return vscode.workspace
    .getConfiguration("manulEngine")
    .get<string>("configFile", DEFAULT_CONFIG_FILENAME);
}
