# Hooks for a long run

Two hooks ship with this skill. Neither is installed automatically: a hook runs on every tool call,
so turning one on is the user's decision. Add the snippets to the **project's**
`.claude/settings.json` (shared) or `.claude/settings.local.json` (this machine only), merging with
any `hooks` already there (RiftMind already has a `PostToolUse` formatter: keep it, add beside it).

## 1. `run-guard` (PreToolUse): the rules of the run, enforced

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|NotebookEdit|Bash|PowerShell",
        "hooks": [
          { "type": "command", "command": "node C:/Users/era92/.claude/skills/long-run-delivery/hooks/run-guard.mjs" }
        ]
      }
    ]
  }
}
```

Then describe the run in `<project>/.claude/run-guard.json` (see `hooks/run-guard.example.json`):

| Key | Meaning | Example |
|---|---|---|
| `protected` | paths, relative to the project root, that the file tools may not edit. A trailing `/` is optional; `docs` protects `docs/…` but not `docs-site/…` | `["modele/", "docs/", "CONCEPTION.md"]` |
| `push` | `"deny"` blocks any `git push`; anything else allows | `"deny"` |
| `forbidTrailers` | text that must not appear in a `git commit` command, case-insensitive | `["Co-Authored-By: Claude"]` |

Behaviour worth knowing:

- No `run-guard.json` found (searched from the working directory upwards) = everything allowed. The
  hook can therefore stay installed globally and only bites in projects that opt in.
- A blocked call returns the reason to the agent, which should then stop and tell the user rather
  than look for another way to do the same thing.
- Lifting a rule is editing the JSON: do it yourself when you change your mind mid-run ("you may
  touch `docs/` now"), so the instruction and the guard agree.
- Limit: protected paths are checked on the file tools only. A shell command that writes into a
  protected folder is not seen. `echo "… git push …"` is refused too (accepted false positive).
- Self-test: `node hooks/run-guard.test.mjs`.

## 2. `preflight` (SessionStart): know the machine before the first command

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "bash C:/Users/era92/.claude/skills/windows-agent-shell/scripts/preflight.sh 3000 5432 7474 7687" }
        ]
      }
    ]
  }
}
```

Its output (shell, Git identity, dirty files, Docker state, which of the listed ports are already
taken, tool versions) is added to the context at the start of the session: about 15 lines, paid
once. On the reference run it would have saved the two turns lost to a local PostgreSQL squatting
port 5432, and the one lost to stopped containers. Pass the ports your project needs.

## What not to automate

- Do not put the gate (tests, lint) in a `Stop` hook for a long run: it runs at every pause and
  pays the full test time each time. Run the gate at the end of each lot instead.
- Do not auto-format in `PostToolUse` during a long run unless the project already does: each
  reformatted file comes back into the context as a change notice.
