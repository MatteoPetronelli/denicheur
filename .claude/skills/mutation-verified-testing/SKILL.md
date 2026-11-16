---
name: mutation-verified-testing
description: Use when a new test passed on its first run, when a test guards a filter, a gate, a threshold or a privacy rule, or before claiming a bug fix is covered. Proves the test can fail by temporarily breaking the code under test, then restoring it. Works in Rust and TypeScript.
metadata:
  category: testing
  triggers: mutation, mutation testing, test passes first time, vacuous test, prove the test fails, regression test, guard test, red green, cargo test, vitest, jest
---

# Mutation-verified testing

A test that has never failed has not shown that it can. The cheapest proof is a hand-made mutation: break the one
line the test is about, run only that test, watch it fail for the stated reason, restore, run again.
Do this for guards (a filter, a lock, a threshold, an exclusion) and for every fix whose test passed immediately.

## Procedure

1. **Name the behaviour** in one sentence ("a partial game is left out of the baseline") and find the line that
   implements it. If you cannot point to one line, the test is probably too broad.
2. **Back up the file by copying it** (`cp file /tmp/file.bak`, or a scratch directory), not by remembering the
   edit. Formatters and hooks may rewrite the line after you edit it, so an "undo" edit can fail to match.
3. **Mutate the smallest thing** that removes the behaviour: delete the filter, return early, drop one condition,
   restore the old constant. One mutation per behaviour.
4. **Run only the targeted test** and read the failure. It must fail on the assertion that states the behaviour
   (the message you wrote), not on a compile error or an unrelated panic. A compile error proves nothing.
5. **Restore from the backup** (`cp`), then `grep` that the original line is back and the marker you added
   (`MUTATION`) is gone. Run the test again: green.
6. If the test **still passes** under the mutation, it is vacuous. Do not weaken the mutation: fix the test
   (see "Findings" below) and mutate again.

Never commit with a mutation present: after restoring, check `git diff` shows only the intended change.

## Rust

```bash
cp crates/x/src/lib.rs /tmp/lib.rs.bak
sed -i 's/\.filter(|m| !is_remake(m))/\.filter(|_m| true)/' crates/x/src/lib.rs   # the mutation
cargo test -p x --test t the_behaviour 2>&1 | grep -E "^test |panicked|left|right"
cp /tmp/lib.rs.bak crates/x/src/lib.rs
```

Several mutations can run in one pass when each has its own test (list the failing tests and match them to the
mutations). Revert the lot before the next run.

## TypeScript

```bash
cp src/baseline.ts /tmp/baseline.ts.bak
sed -i 's/if (game.partial) continue;/\/\/ MUTATION/' src/baseline.ts
npx vitest run -t "partial game" 2>&1 | tail -20      # or: npx jest -t "partial game"
cp /tmp/baseline.ts.bak src/baseline.ts
```

For a UI rule, mutate the component's condition and run the component test; for a type-level guarantee, a
`// @ts-expect-error` line that stops erroring after the mutation plays the same role.

## Findings this practice produced (examples)

- A test "disabled tag does not demote another" passed under the mutation: the evaluator already checked
  `enabled` itself, so the test could never see the bug. Only a tag excluded by its `modes` list (applied after
  the evaluators run) exercised the faulty line. The test was rewritten around that case.
- A test asserting a live-game record is withheld failed under the mutation, which also proved the record really
  was being returned before the fix (the guard was not vacuous, and the leak was real).
- Raising a per-champion threshold from 8 to 3 and limiting a journal check to the primary cause each made a
  different test fail, confirming both tests pointed at their own behaviour.
- A parser test built from a real-format sample (string-valued numbers, empty name field) failed immediately and
  exposed two parser bugs that hand-written numeric fixtures had hidden.

## Rules

- The mutation must be a behaviour the user cares about, not a typo. Syntax mutations are what the compiler is for.
- Keep the failing output in your report in one line ("fails with: partial game counted: left 6, right 5").
- If a mutation cannot be run (no way to execute the test, generated code), say the test is unproven rather than
  calling it covered.
