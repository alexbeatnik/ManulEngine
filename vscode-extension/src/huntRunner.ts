import * as path from "path";
import * as fs from "fs";
import { spawn, ChildProcess } from "child_process";
import * as vscode from "vscode";

/** Locate the manul CLI: checks user setting, .venv/bin, then PATH. */
export function findManulExecutable(workspaceRoot: string): string {
  const custom = vscode.workspace
    .getConfiguration("manulEngine")
    .get<string>("pythonPath", "")
    .trim();
  if (custom) {
    return custom;
  }

  const venvBin = path.join(workspaceRoot, ".venv", "bin", "manul");
  const venvScripts = path.join(workspaceRoot, ".venv", "Scripts", "manul.exe");
  if (fs.existsSync(venvBin)) {
    return venvBin;
  }
  if (fs.existsSync(venvScripts)) {
    return venvScripts;
  }
  return "manul"; // fall back to PATH
}

/** Spawn manul <huntFile> and stream output. Resolves with exit code. */
export function runHunt(
  manulExe: string,
  huntFile: string,
  onData: (chunk: string) => void,
  token?: vscode.CancellationToken
): Promise<number> {
  return new Promise((resolve, reject) => {
    let proc: ChildProcess;
    try {
      proc = spawn(manulExe, [huntFile], {
        cwd: path.dirname(huntFile),
        env: { ...process.env },
      });
    } catch (err) {
      reject(err);
      return;
    }

    proc.stdout?.on("data", (d: Buffer) => onData(d.toString()));
    proc.stderr?.on("data", (d: Buffer) => onData(d.toString()));
    proc.on("close", (code) => resolve(code ?? 1));
    proc.on("error", reject);

    token?.onCancellationRequested(() => {
      proc.kill();
      resolve(1);
    });
  });
}
