---
name: browser-proof
description: Use when a web interface was built or changed and nobody has looked at it - before claiming a UI works, when the only checks so far are unit tests and HTTP 200s, when a demo scenario must be verified end to end, when accessibility (contrast, keyboard, labels) is required but untested, or when a form or Server Action must be exercised without a browser.
metadata:
  category: technique
  triggers: Playwright, e2e, screenshot, accessibility, contrast, WCAG, keyboard navigation, Server Action, demo scenario, never seen the UI, visual check
---

# Browser proof

An agent that has only run unit tests and `curl` has not seen its interface. On the reference run
the first real browser pass found what 126 green tests had not: a field without a label on every
repeated form, and a graph whose labels overlapped. It also took 17 seconds.

Three levels, cheapest first. Stop at the level the claim needs.

## Level 1: post a real form, no browser (`scripts/post_form.py`)

Proves that a server-rendered form and its handler work together: it fetches the page, picks the
form that contains the fields you name, keeps its hidden inputs (including the framework's action
ids), posts it as a browser would, and prints the status, the redirect and any `role="alert"` text.

```bash
python scripts/post_form.py http://localhost:3000/connexion email=admin@x.test motDePasse=wrong
python scripts/post_form.py http://localhost:3000/connexion email=admin@x.test motDePasse=right \
       --then http://localhost:3000/admin   # same cookie jar: checks the session really opened
```

Good for: login, one create form, one validation error. Not for anything that needs JavaScript.
Trap: under Git Bash give `--then` a full URL (a bare `/admin` is rewritten into a Windows path).
Trap: when several forms share the same field names (a create form and its edit forms), the first
match wins; add `--index N` or name a field only the target form has.

## Level 2: play the scenario in a browser (Playwright)

One test that walks the demo scenario the way the user will, with a second browser context when
something must update live. Rules that kept the reference test stable:

- **Select by role and label**, never by CSS class: `getByRole("button", { name: "…" })`,
  `getByLabel("…")`. If you cannot, the interface is missing a label: fix the interface.
- **Wait on a visible fact**, not on time: a heading whose count changed (`Manches (2)`), a status
  word. `isVisible()` does not wait: assert that the page loaded before branching on it.
- **Scope to the form** when a page repeats one:
  `page.locator("form", { has: page.getByRole("button", { name: "Save" }) })`.
- **Exact names** when one label contains another (`Finale` / `Demi-finales`): `{ exact: true }`.
- **Start from a fresh database** and say so at the top of the file; a scenario that creates
  "Ynov Cup" twice proves less the second time.
- **Take screenshots at each milestone and read them.** `page.screenshot({ path, fullPage: true })`,
  then open the PNG with the image-reading tool. A full-page capture shows a sticky header in the
  middle of the page: that is the capture, not a bug.
- **When the test fails, suspect the test first.** Three of the four failures on the reference run
  were a selector or a missing wait. Read the error and the failure screenshot before touching the
  product.

Install once: `npm i -D --save-exact @playwright/test && npx playwright install chromium`
(about 125 MB). Start from `templates/playwright.config.ts`.

## Level 3: accessibility, measured (`templates/accessibility.spec.ts`)

Copy the template and adapt the selectors. It checks, in the real browser:

- **Contrast**: the actual text colour against the actual painted background (ancestors' backgrounds
  composited, any CSS colour format), at least 4.5:1. Measure one element per text style of the
  theme. A surprising ratio on a known-good element means the selector caught something else
  (an empty decorative dot, a hidden template): inspect before "fixing" the palette.
- **Keyboard**: the first Tab reaches a skip link; every focused element shows a focus ring; a
  login and a navigation are done without the mouse.
- **Labels**: every visible input, select and textarea has an accessible name. Run it on pages with
  *repeated* forms: duplicate `id`s leave every field but the first unlabeled.
- **Not colour alone**: states are written (a "live" badge says "live"), winners are announced to
  screen readers, a chart has a text alternative and a table.

## What this does not replace

A human looking at the real thing once. Say which level you reached: "posted the login form",
"scenario green in Chromium, screenshots read", "contrast and keyboard measured". Never "the UI works".

## Not a web app?

Same idea, other driver: a CLI gets a transcript of a real invocation; a Claude Code plugin gets
`claude plugin test` plus a screenshot of its pane; a desktop app (Tauri) gets its front-end served
alone with the IPC mocked, then levels 2 and 3 apply.
