# Retrospective: the "Bracket" run (12-13 Nov 2026)

A school project: audit a group repo, complete the technical base (Sonnet 5.5), then frame and
deliver a Next.js + PostgreSQL + Neo4j application in six lots under a `/goal` (Fable 5.2, Pro plan).
Result: 20 commits, 126 unit/integration tests, 4 browser tests, checklist proven on a clean clone.

## Measured consumption

From `scripts/tokens_by_commit.py` (k = thousand tokens). `new` = input written to the cache,
`read` = input re-read from the cache, `read/turn` = context size.

| Work | Model | Turns | Out | New | Read | Read/turn |
|---|---|---:|---:|---:|---:|---:|
| Audit + DDL, generator, compose, README (5 commits) | Sonnet 5.5 | 22 | 38 k | 113 k | 2 382 k | ~110 k |
| Framing + lot 0 (scaffold, Docker) | Fable 5.2 | 29 | 59 k | 225 k | 6 240 k | 215 k |
| Lot 1 (public pages, 5 queries) | Fable 5.2 | 10 | 51 k | 67 k | 2 893 k | 289 k |
| Lot 2 (auth, rights, CRUD) — one usage pause | Fable 5.2 | 21 | 62 k | 408 k | 7 415 k | 353 k |
| Lot 3 (tournament engine) | Fable 5.2 | 11 | 53 k | 60 k | 4 750 k | 432 k |
| Lot 4 (graph + live) | Fable 5.2 | 14 | 30 k | 39 k | 6 754 k | ~485 k |
| Lot 5 + clean-clone fixes — one usage pause | Fable 5.2 | 16 | 26 k | 504 k | 7 849 k | ~490 k |
| Browser tests, bonuses, accessibility — one pause | Fable 5.2 | 27 | 35 k | 611 k | 14 615 k | ~540 k |
| Docs asked afterwards — one pause | Fable 5.2 | 13 | 13 k | 1 157 k | 6 707 k | ~515 k |
| **Total** | | **217** | **445 k** | **3 383 k** | **69 102 k** | **318 k** |

The total also counts a short earlier session on another model and a few turns outside these rows.

What the numbers say:

1. **Output is negligible.** 445 k produced against 69 M re-read. Writing less code would not have
   changed the bill; a smaller context would have.
2. **The context never shrank.** 140 k per turn at the start, 618 k at the end. Lot 3, the hardest,
   cost fewer turns than lot 0 but twice the tokens per turn, only because it came later.
3. **Each usage-limit pause cost a full rewrite of the context** (cache expired): 408 k, 498 k,
   574 k, then 1 156 k. Four pauses = 2.6 M tokens spent re-loading history that three small
   planning files already summarised.
4. **Fewer, bigger turns win.** The lots with 10-11 turns (1, 3) were the cheapest per feature.
   Lot 0 took 29 turns of trial and error on tooling.

What would have halved the bill: starting a fresh session at each lot boundary (or at least after
each pause) with the plan files, and silencing the formatter notices.

## Workflow: what worked

- **Framing questions in batches, recommendation first.** Eleven questions in three rounds settled
  everything; none had to be reopened. The most valuable one was "what do I cut first".
- **Checking the registry before recommending a stack.** It showed the auth library was still in
  beta and could not do what the spec asked; that became a question instead of a mid-run surprise.
- **Plan files on disk.** Four pauses and one context of 600 k later, the run resumed at the right
  lot every time.
- **Rules as pure functions, tests first.** The tournament engine passed its 21 integration tests
  on the first run because the rules under it were already proven.
- **A drift test for copied code.** Queries copied from a teammate's file are compared to the
  source by a test; the copy cannot silently diverge.
- **The clean clone.** Two real defects found only there.
- **A browser test added late.** It found a real accessibility defect (duplicate field ids) and let
  the agent finally look at the interface through screenshots.

## Workflow: what went wrong

| What happened | Cost | Rule to keep |
|---|---|---|
| Long heredocs with an apostrophe failed to parse, three times, nothing was written | 3 lost turns | Write source files with the file tool, keep heredocs for short ASCII scripts |
| `cd app` in one call, relative paths in the next: a "commit + push" ran from the wrong folder | 1 lost turn, a false "pushed" narrowly avoided | Start every command with an absolute `cd`; check `git log -1` before claiming a commit |
| A background task started at minute 5 was still "running" a day later | a spurious wake-up | Start GUI apps detached; stop stale background tasks |
| The machine slept; containers stopped; tests failed on connection | 1 turn of diagnosis | On a connection error, check the service is up before reading the code |
| A local PostgreSQL already owned port 5432 | 2 turns | Preflight the ports (`windows-agent-shell/scripts/preflight.sh`) |
| Integration tests would have overwritten demo data in the shared graph database | caught before damage | Tests get their own database or a reserved id range, and a switch that disables side effects |
| The checklist was ticked before the browser test existed; the stop hook refused three times | 3 extra rounds | Write the stop condition so each item is a command or an explicit human step; ask the human for their step |
| A bundled "tests && commit && commit && push" was refused as a whole | 1 turn | One concern per command; a push needs its own go-ahead |
| The first test failures were the tests' fault (wrong selector, timing) three times | small | Read the failure before touching the product; a 1.7:1 contrast on a known-good badge is a bad selector |
| The formatter rewrote dozens of files per lot; each came back as a notice | context bloat | Format once, at the end of the lot |

## Technical notes worth keeping

- **Scaffolds lie about defaults.** The framework generator enabled a new caching model the plan had
  not accounted for. Read the generated config and the bundled docs before the first line of code.
- **Idempotent seeding.** A seed service that drops and recreates the schema on every start destroys
  user data and silently drops foreign keys from other schemas. Guard it ("only if empty").
- **Unordered collections break determinism**: sorting a `set` of strings gave a different order on
  every run (hash randomisation). Sort first, then shuffle with the seeded generator.
- **Module singletons** in a bundler-based server may exist once per bundle: keep shared state on
  `globalThis`.
- **A push after the database commit must never fail the write**: catch, log, and keep a full
  rebuild command as the safety net.
- **Reverse-proxy-less containers report `0.0.0.0` as their host**: set the public URL explicitly or
  redirects break on Windows browsers.
- **Empty directories are not in Git**; a Dockerfile `COPY` of one fails only on a clone.
- **CRLF on checkout** (`core.autocrlf`) fails a formatter check only on a Windows clone.
- **Repeated forms need unique field ids** (`useId`), or only the first field of each kind has a label.
