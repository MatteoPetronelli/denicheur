// node run-guard.test.mjs   — self-check of the guard's decisions
import assert from "node:assert/strict";
import { decide } from "./run-guard.mjs";

const root = process.platform === "win32" ? "C:\\proj" : "/proj";
const p = (rel) => (process.platform === "win32" ? `C:\\proj\\${rel.replace(/\//g, "\\")}` : `/proj/${rel}`);
const config = { protected: ["modele/", "docs", "CONCEPTION.md"], push: "deny", forbidTrailers: ["Co-Authored-By: Claude"] };
const edit = (file) => decide({ tool_name: "Edit", tool_input: { file_path: file }, cwd: root }, config, root);
const bash = (command, c = config) => decide({ tool_name: "Bash", tool_input: { command } }, c, root);

assert.match(edit(p("modele/postgres/schema.sql")), /protected path "modele\/"/);
assert.match(edit(p("docs/adr/0001.md")), /protected/);
assert.match(edit(p("CONCEPTION.md")), /protected/);
assert.equal(edit(p("app/src/page.tsx")), null);
assert.equal(edit(p("modele-bis/x.sql")), null, "a prefix is not a folder");
assert.equal(edit(p("docs-site/x.md")), null);
assert.equal(edit(process.platform === "win32" ? "C:\\other\\modele\\x" : "/other/modele/x"), null, "outside the project");

assert.match(bash("cd repo && git push origin main"), /pushing is not allowed/);
assert.match(bash("git -C repo push"), /pushing/);
assert.equal(bash("git push", { push: "allow" }), null);
assert.equal(bash("git log --oneline | grep push"), null, "the word push after a pipe is not a push");
// Known false positive, accepted: `echo "git ... push"` is blocked too. Better one refused echo than one unwanted push.

assert.match(bash('git commit -m "feat: x\n\nCo-authored-by: Claude Fable <noreply@anthropic.com>"'), /forbids/);
assert.equal(bash('git commit -m "feat: x\n\nCo-authored-by: Thomas <t@example.com>"'), null);
assert.equal(bash('echo "Co-Authored-By: Claude"'), null, "only commits are checked");
assert.equal(decide({ tool_name: "Read", tool_input: { file_path: p("modele/x") } }, config, root), null);
assert.equal(decide({ tool_name: "Edit", tool_input: { file_path: p("modele/x") } }, {}, root), null, "empty config allows");

console.log("run-guard: all checks passed");
