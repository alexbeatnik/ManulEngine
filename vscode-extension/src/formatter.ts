import * as vscode from "vscode";

/**
 * Document formatter for .hunt DSL files.
 *
 * Applies YAML/Python-like visual hierarchy:
 *   0 spaces — @headers, STEP markers, DONE., [SETUP]/[TEARDOWN] block markers, top-level comments
 *   4 spaces — action commands, comments inside STEP or hook blocks
 */

const INDENT = "    "; // 4 spaces

/** Lines that are always flush-left (0 indent). */
const RE_HEADER = /^\s*@/;
const RE_STEP = /^\s*(?:\d+\.\s*)?STEP\s*\d*\s*:/i;
const RE_DONE = /^\s*(?:\d+\.\s*)?DONE\s*\.?\s*$/i;
const RE_HOOK_OPEN = /^\s*\[(SETUP|TEARDOWN)\]\s*$/i;
const RE_HOOK_CLOSE = /^\s*\[END\s+(SETUP|TEARDOWN)\]\s*$/i;
const RE_COMMENT = /^\s*#/;

export class HuntDocumentFormatter implements vscode.DocumentFormattingEditProvider {
  provideDocumentFormattingEdits(
    document: vscode.TextDocument,
    _options: vscode.FormattingOptions,
    _token: vscode.CancellationToken
  ): vscode.TextEdit[] {
    const edits: vscode.TextEdit[] = [];
    let insideBlock = false; // true when inside a STEP group or hook block

    for (let i = 0; i < document.lineCount; i++) {
      const line = document.lineAt(i);
      const raw = line.text;
      const trimmed = raw.trimEnd();    // strip trailing whitespace always
      const stripped = trimmed.trimStart();

      // ── Empty / blank lines — preserve as empty ──────────────────────
      if (stripped.length === 0) {
        if (raw !== "") {
          edits.push(vscode.TextEdit.replace(line.range, ""));
        }
        continue;
      }

      let desired: string;

      // ── Zero-indent tokens ───────────────────────────────────────────
      if (RE_HEADER.test(stripped)) {
        // @context:, @title:, @tags:, @var:, @data:
        desired = stripped;
      } else if (RE_STEP.test(stripped)) {
        // STEP 1: Label  or  STEP: Label
        insideBlock = true;
        desired = stripped;
      } else if (RE_DONE.test(stripped)) {
        insideBlock = false;
        desired = stripped;
      } else if (RE_HOOK_OPEN.test(stripped)) {
        // [SETUP] / [TEARDOWN]
        insideBlock = true;
        desired = stripped;
      } else if (RE_HOOK_CLOSE.test(stripped)) {
        // [END SETUP] / [END TEARDOWN]
        insideBlock = false;
        desired = stripped;
      } else if (RE_COMMENT.test(stripped)) {
        // Comments: indent only when inside a block
        desired = insideBlock ? INDENT + stripped : stripped;
      } else {
        // ── Action lines — always 4-space indent ─────────────────────
        desired = INDENT + stripped;
      }

      if (raw !== desired) {
        edits.push(vscode.TextEdit.replace(line.range, desired));
      }
    }

    return edits;
  }
}
