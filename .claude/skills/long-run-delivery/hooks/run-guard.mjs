#!/usr/bin/env node
// PreToolUse guard for long runs. Turns the rules of a run into something that cannot be forgotten:
//   - "protected": paths the agent must not edit (deliverables of other people, graded files…)
//   - "push": "deny" blocks `git push` (default "allow")
//   - "forbidTrailers": text that must not appear in a `git commit` command (e.g. an AI co-author line)
// Config: <project>/.claude/run-guard.json, looked up from the working directory upwards.
// No config = the hook allows everything. Exit code 2 + a message on stderr blocks the tool call.
//
// shortcut: protected paths are enforced on the file tools only, not on what a shell command writes;
// add a sandbox or OS permissions if the files must be tamper-proof.

import { existsSync, readFileSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

/** Pure decision: returns the reason to block, or null. Exported for the self-test. */
export function decide(input, config, root) {
  const tool = input.tool_name ?? "";
  const args = input.tool_input ?? {};

  if (["Edit", "Write", "NotebookEdit", "MultiEdit"].includes(tool)) {
    const cible = args.file_path ?? args.notebook_path;
    if (!cible) return null;
    const rel = relative(root, isAbsolute(cible) ? cible : resolve(input.cwd ?? root, cible)).replace(/\\/g, "/");
    if (rel.startsWith("..")) return null; // outside the project: not this guard's business
    const hit = (config.protected ?? []).find((p) => rel === p.replace(/\/$/, "") || rel.startsWith(p.replace(/\/?$/, "/")));
    return hit ? `run-guard: "${rel}" is under the protected path "${hit}" (.claude/run-guard.json). Do not edit it; if the user asked for this change, they must lift the protection.` : null;
  }

  if (tool === "Bash" || tool === "PowerShell") {
    const cmd = String(args.command ?? "");
    if (config.push === "deny" && /\bgit\b[^|;&\n]*\bpush\b/.test(cmd))
      return "run-guard: pushing is not allowed in this run (.claude/run-guard.json: push = deny). Commit locally and tell the user.";
    if (/\bgit\b[^|;&\n]*\bcommit\b/.test(cmd)) {
      const trailer = (config.forbidTrailers ?? []).find((t) => cmd.toLowerCase().includes(t.toLowerCase()));
      if (trailer) return `run-guard: this commit message contains "${trailer}", which this project forbids. Remove that line.`;
    }
  }
  return null;
}

function findConfig(start) {
  for (let dir = resolve(start); ; dir = dirname(dir)) {
    const f = join(dir, ".claude", "run-guard.json");
    if (existsSync(f)) return { root: dir, config: JSON.parse(readFileSync(f, "utf8")) };
    if (dirname(dir) === dir) return null;
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  let brut = "";
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (c) => (brut += c));
  process.stdin.on("end", () => {
    try {
      const input = JSON.parse(brut || "{}");
      const trouve = findConfig(input.cwd ?? process.cwd());
      const raison = trouve && decide(input, trouve.config, trouve.root);
      if (raison) {
        console.error(raison);
        process.exit(2);
      }
    } catch (e) {
      console.error(`run-guard: ignored (${e.message})`); // a broken guard must not block the session
    }
    process.exit(0);
  });
}
