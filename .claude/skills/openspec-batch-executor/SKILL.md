---
name: openspec-batch-executor
description: Use when executing a roadmap or an OpenSpec change lot by lot from a tasks.md checklist (several lots in one long session), when a user says "on passe au lot N", or when a multi-lot run must stay within a usable context budget and end with the change archived.
metadata:
  category: workflow
  triggers: openspec, tasks.md, roadmap, lot, lots, batch, checklist, archive change, specs, gate, long session, compact, context
---

# OpenSpec batch executor

A roadmap of lots is one long conversation. This skill keeps each lot small, proven and closed, and keeps the
context from silently growing until every turn is expensive. Project skills (invariants, ToS or security guards,
language skills) still apply inside a lot: load the ones the lot names, once.

## Before a lot

1. Read the lot in **both** places: the roadmap (goal, files, invariants, end condition) and `tasks.md` (the
   numbered tasks). They can disagree, and so can the user's one-line request. If the request describes other
   work than the written lot, say so in one sentence, do what was explicitly asked, and leave the written tasks
   unticked. Do not tick work that was not done.
2. Do the lot's **blocking first step** before any change (a bench, a scan, a data check) and show its output.
   A lot can end there: if the premise is false (a pattern that does not repeat, no recording of the needed
   kind), stop and document instead of building.
3. Measure instead of assuming. Several lots of the session this comes from changed course on a measurement:
   a parser that failed on every real file, a comment claiming something the data contradicted, a metric that was
   0 on all samples. A claim in code or docs gets a number or it is worded as unverified.

## During a lot

- Smallest change that meets the task. Add new fixtures, tests and files at the **end** of ordered lists so
  existing numbering and snapshots stay byte-identical; renumbering ground-truth files is a regression.
- Write the test, see it fail for the right reason, then fix. When the test passes first time, prove it can fail
  (skill `mutation-verified-testing`).
- A guarded behaviour (privacy, ToS, security) is audited as its own step, with file:line evidence and a list of
  what was not checked. A gap found on the way is fixed in the same lot only when the fix is small and tested;
  otherwise it is reported and the decision goes to the user.
- On Windows with a bash tool, a heredoc containing apostrophes can be rejected whole. Write such files with the
  file-write tool and append with `cat`; run multi-line edits through a small script file.

## End-of-lot checklist (every lot, in this order)

1. Tick the lot's boxes in `tasks.md` (only the ones really done; the gate box last).
2. Run the project gate and read the real output: format check, linter with warnings as errors, the full test
   suite with the count, the project's regression runner, any invariant test. Report numbers, not "green".
3. Update derived docs the lot touched: counts of tests and fixtures, README sections, schema tables.
4. Refresh the code graph if the project has one (`graphify update .` in RiftMind).
5. Commit only when the user asked. Message: conventional header (70 characters at most), a body that says what
   changed and why, the measured effect, what is **not** covered, and any data compatibility note (for example
   "stored diagnoses were produced under the previous rules"). Follow the repository's commit skill for
   attribution lines; do not add trailers it forbids. Stage files by name, never `git add -A` blindly.
6. Final message: what was done, what was measured, what was not checked (app not run, UI only syntax-checked,
   synthetic data only), and the decisions left to the user.

## Context hygiene

Long runs get slow and costly because every turn re-reads everything. Therefore:

- **Propose `/compact` or `/clear` every 2 lots**, or as soon as the context passes about 250k tokens,
  whichever comes first. Say it in one line at the end of the lot, with what would be lost (nothing that is not in
  git, `tasks.md` or the roadmap) so the user can accept at no risk. Never compact on your own.
- Before the proposal, make sure the next session can resume from files: ticked `tasks.md`, committed work,
  and a one-line "next lot" in the final message.
- Keep large outputs out of the conversation: write bench outputs to a scratch file and quote the relevant lines.
- At the end of the roadmap, if the user runs a router that carries a plan memory across turns
  (the `dynamic-orchestrator` plugin), remind them to clear that plan memory (`/orchestrator plan clear`, as the
  user named it) so the finished plan stops forcing a heavy tier on unrelated turns.

## Closing the change (last lot only)

1. All boxes ticked and the gate green on the final tree.
2. `git mv openspec/changes/<change> openspec/changes/archive/<change>` (history kept).
3. Copy each `specs/<capability>/spec.md` to `openspec/specs/<capability>/spec.md`. The change holds deltas
   (`## ADDED Requirements`): in the main spec use `# <capability> Specification`, a one-line `## Purpose`, and
   `## Requirements`. If the OpenSpec CLI is installed, `openspec archive <change>` does this.
4. Update references to the old path (roadmap, docs). Keep versioned documents the change cites as evidence.
5. Remove only files the user named and that are not versioned; keep a copy of anything untracked before deleting.
6. Commit with a message that covers the last lot and the closure.

## Never

- Tick a task that was not done, or call a gate green without having run it.
- Renumber or rewrite ground-truth files to make a test pass.
- Push, archive or delete beyond what the user asked.
