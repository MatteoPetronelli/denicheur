---
name: long-run-delivery
description: Use when delivering several lots of work in one long autonomous run (a /goal, an overnight session, a usage-limited plan), when a run must survive usage-limit pauses or compaction, when the user asks how many tokens each lot cost, or when "done" must be proven on a clean clone before handing back.
metadata:
  category: technique
  triggers: /goal, long run, lots, usage limit, tokens per lot, clean clone, definition of done, overnight, run-guard
---

# Long-run delivery

How to ship a multi-lot piece of work in one run without losing the thread, burning the budget, or
declaring victory too early. Distilled from a real 6-lot run (217 turns, 20 commits); the measured
data and the mistakes are in [references/retrospective-bracket.md](references/retrospective-bracket.md).

Works with any model and any stack. The project only has to say what its **gate** is (the commands
that must pass). Ready-made settings for RiftMind and dynamic-orchestrator:
[references/projects.md](references/projects.md).

## The run in five moves

1. **Frame before you build.** Read everything, then ask the user only what the spec does not
   settle: gaps between the spec and the existing code, product behaviour, look and feel, demo
   content, and *what to cut first if the budget runs short*. Batch 1-4 questions, recommendation
   first. Verify real versions on the registry before recommending a stack (a "stable" library may
   still be in beta).
2. **Write the plan to disk** (`planning-with-files`): `task_plan.md` (lots, one test per acceptance
   criterion, the command that proves each lot, the cut order), `findings.md` (the user's answers,
   verbatim), `progress.md` (one line per lot: commit, proof). These files, not the conversation,
   are what a resumed session reads.
3. **One lot = test first, gate, launch, commit.** Pure rules first with their tests, then the code
   that touches I/O, then the screens. After each lot: run the gate, launch the real thing, hit it
   (`curl`, a CLI call, a test harness), commit, update `progress.md`. Never move on with a red gate.
4. **Prove it where it will be judged.** Before saying "done", run
   `scripts/clean_clone_check.sh` : a fresh `git clone` in a temp folder, then the gate. On the
   reference run this caught two defects that every local check had missed (an empty directory Git
   does not track, CRLF line endings on checkout).
5. **Report what was verified, how, and what was not.** If a human step remains, ask for it with
   the question tool instead of ending on "it is up to you".

## Budget rules (measured, not guessed)

- **Context size is the bill.** Output tokens were 0.6 % of the traffic; re-reading the context was
  the rest, and it grew from 140 k to 618 k tokens per turn. Check with
  `python scripts/tokens_by_commit.py` : if `read/turn` passes ~300 k, compact or restart.
- **A usage-limit pause costs a full context rewrite** (the cache has expired): 0.4 to 1.2 M tokens
  each time on the reference run. After a pause, prefer a *new session* that reads `task_plan.md`,
  `findings.md` and `progress.md` over resuming a 500 k conversation.
- **Do not print what you will not read.** Pipe test runs through a filter (`| tail`, `| grep -E
  "passed|failed"`), silence Git's line-ending warnings (`2>/dev/null`), and never let a formatter
  rewrite 100 files in a turn where you also print them.
- **Format once per lot, not once per file**: every reformatted file comes back as a "changed on
  disk" notice in the context.
- **Batch file writes** in one turn; one turn = one full context re-read.

## Stop conditions that hold

A stop condition is checked by someone else (a hook, a reviewer, the user). Write it so each item
is either provable by a command or explicitly a human step:

- name the command and the expected output for every item;
- if the spec says "a human replays it afterwards", say so in the condition, or plan to ask;
- never tick a checklist before the last test was added; re-run the whole proof after any change.

## Guard rails as hooks

`hooks/run-guard.mjs` is a PreToolUse hook that reads `.claude/run-guard.json` in the project and
blocks: edits to protected paths, `git push` when pushing is not allowed, and commits carrying a
forbidden trailer. It turns the rules of the run ("never touch `modele/`", "do not push", "no AI
co-author") into something that cannot be forgotten at turn 180. Setup:
[references/hooks.md](references/hooks.md).

## Scripts

| Script | Use |
|---|---|
| `scripts/tokens_by_commit.py` | real token usage per commit (= per lot) or per hour, from the transcripts |
| `scripts/clean_clone_check.sh "cmd" ["cmd" …]` | fresh clone in a temp folder, run the gate there, clean up |
| `hooks/run-guard.mjs` | PreToolUse guard (protected paths, push policy, commit trailers) |

## Common mistakes

| Mistake | Fix |
|---|---|
| Chaining tests + commits + push in one shell command | One concern per command: a refused or failed step must not take the others down, and a push needs its own explicit go-ahead |
| Trusting "it runs on my machine" | Clean clone, every time, before "done" |
| Testing only through services | Drive the real interface at least once (browser, CLI, plugin harness) and *look* at it: see `browser-proof` |
| Integration tests writing to the demo database | A separate database or an id range reserved for tests, cleaned afterwards |
| Declaring a lot done from memory | Write the proof line in `progress.md` at the moment you have the output |
| Answering a contradiction by guessing | When two instructions disagree (spec says "do not push", user said "push"), ask once, write the answer in `findings.md` |
