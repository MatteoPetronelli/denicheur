# Dénicheur — Full OpenSpec Roadmap (C0 → C7)

> **For Claude (executor: Sonnet 5.5, effort medium).** This file is the single source of truth for building
> Dénicheur. Execute it **one OpenSpec change at a time, one lot at a time**, following the protocol in §2.
> Do not redesign: architecture, contracts and test expectations below are decided. If reality contradicts
> the plan (an API answers differently, a fixture does not match), stop the lot, report the measurement, and
> let the user decide (skill `openspec-batch-executor`, "Before a lot", point 2).

**Goal:** a personal job radar that collects alternance/stage offers from legal sources, filters them (25 km
around Mareil-Marly, rules), scores them with `claude-sonnet-5-5`, and sends a French Telegram digest + instant
alerts, then supports drafts, application tracking, spontaneous applications, e-mail alerts and a dashboard.
The final send of any application is **always human**.

**Architecture:** one Python package `src/denicheur` (pipeline, DB, LLM, Telegram) run by GitHub Actions
(cron) and by a thin Vercel Python function (Telegram webhook) that imports the same package; one Postgres
(Neon) shared by both; a SvelteKit dashboard in `web/` reading the same Postgres. SQLite only for local dev
and tests.

**Tech stack:** Python ≥3.12 (local interpreter is 3.13), httpx, pydantic v2, SQLAlchemy 2, Alembic,
psycopg 3, anthropic (Python SDK 1.x), PyYAML, python-dotenv, tzdata; pytest, ruff, mypy. Web: SvelteKit +
`postgres` (npm). Infra: GitHub Actions, Vercel, Neon, Telegram Bot API, Gmail IMAP.

---

## 0. Context

The repo holds only docs (`Denicheur-specifications.md`, `handoff.md`, `README.md`), an API test script
(`test_france_travail.py`), real LBA results (`ft_test_results.json`, gitignored, 3 blocks: 16/14/15 jobs,
150 recruiters each), a CSV of 150 nearby IT companies (`entreprises_spontanees_mareil-marly.csv`, `;`
separated, UTF-8 BOM) and an empty OpenSpec setup (`openspec/config.yaml`, schema `spec-driven`, CLI 2.0.0).
No application code. The user wants a complete, decided plan so a cheaper model can implement it.

Measured facts the plan relies on (from `ft_test_results.json`, first block, today = 2026-11-16):

| # | Company (`workplace.name`) | Title (short) | partner | km | Expected fate |
|---|---|---|---|---|---|
| 1 | ITIC PARIS | Développeur / Développeuse de sécurité des SI | offres_emploi_lba | 23.2 | **kept** (`des_que_possible`, 6 months, diploma 7) |
| 2–13 | `null` (Wavestone) | "Stage de fin d'études / Alternance - …" ×6 titles, each twice | France Travail | 9.3 | 12 → 6 after dedupe → **dropped** (`mots_cles_absents`; 5 of 6 also older than 30 days) |
| 14 | CAPGEMINI | Data Business Analyste **Confirmé** H/F | Hellowork | 14.9 | **dropped** (`mot_exclu:confirme`) |
| 15 | MUTUELLE GENERALE EDUCATION NATIONALE | Alternant·e RH - Paie et SIRH | Hellowork | 19.8 | **dropped** (`mots_cles_absents`) |
| 16 | SAS WOODOO | ALTERNANCE - Développeur·se Full Stack Industrie 4.0 | Jobs that make sense | 19.8 | **kept, `lieu_a_verifier=True`** (description names Troyes / La Chapelle-Saint-Luc) |

16 jobs → 10 distinct URLs → **2 retained offers**. Coordinates are `[lon, lat]`. 13/16 have
`target_diploma = null`.

---

## 1. Decisions (locked — do not revisit)

| Topic | Decision |
|---|---|
| Change granularity | One OpenSpec change per phase (C0…C7), each `tasks.md` split into numbered lots (L1, L2…). One lot per session turn-block; gate after every lot. |
| Order | C0 bootstrap → C1 MVP alternance digest → C2 e-mail alerts → C3 Adzuna stage → C4 interactive bot → C5 drafts + Gmail drafts → C6 spontaneous applications → C7 dashboard. (Spec order moved e-mail alerts and spontaneous earlier because handoff §3/§5 measured that LBA alone sees very few dev offers; dashboard last per spec §16.) |
| DB | SQLAlchemy 2 + Alembic **from C1**. SQLite for local/tests; **Neon Postgres as soon as the job runs in GitHub Actions (C1 L6)**, because a runner's SQLite file is lost between runs and idempotence would break. All six spec tables created in the first migration. |
| Web | Telegram webhook = Vercel **Python** function `api/telegram.py` importing `src/denicheur`. Dashboard = **SvelteKit** in `web/` (separate Vercel project), C7. |
| Diploma | Alternance prepares **Bac+3** → `niveau_vise: 6`. Bac+5 (`7`) offers get a score malus + ⚠️ alert, never eliminated. Do **not** pass `target_diploma_level` to the LBA API (it would hide the 13/16 offers with null diploma). |
| Fixture | Commit `tests/fixtures/lba_search.json` = first block of `ft_test_results.json` (16 jobs + 150 recruiters, public ad/company data). `ft_test_results.json` itself stays gitignored. |
| Gmail | IMAP + app password, stdlib `imaplib`. Read only label `Denicheur`; create drafts via `APPEND` to `[Gmail]/Drafts`. Never send. |
| HTTP | Our code uses `httpx` (sync). The Anthropic SDK 1.x uses its own `httpx2` internally: never pass our httpx client to it. |
| Tests | No network in tests. HTTP mocked with `httpx.MockTransport`; LLM with a fake class implementing the same protocol; time injected (`now` parameter), never `datetime.now()` inside logic. |
| Telegram lib | None. Plain Bot API over httpx (`sendMessage`, `answerCallbackQuery`, `editMessageReplyMarkup`, `setWebhook`, `getUpdates`). |
| Cost guard | Besides `llm_max_appels_jour`, add `llm_budget_mensuel_eur: 5.0`; scoring stops when month-to-date `cout_eur` ≥ budget. (150 calls/day at ≈0.01 $/call would be ≈45 $/month, over the spec's 5 € goal.) |
| Quality gate | `py -m ruff format --check .` · `py -m ruff check .` · `py -m mypy src` · `py -m pytest -q`. pre-commit: skipped (YAGNI). |

---

## 2. Execution protocol (how Sonnet runs this plan)

For each change **Cn**:

1. **Propose** — run skill `openspec-propose` with the change name and the text of the "Cn" section below
   (Why / What / Lots). `design.md` copies the relevant parts of §3 (architecture) verbatim; `tasks.md` has one
   `## Lot n` heading per lot, numbered checkboxes, gate box last. `specs/<capability>/spec.md` uses
   `## ADDED Requirements` with `#### Scenario:` blocks taken from the lot's test expectations.
   Then `openspec validate <change>`.
2. **Execute** — skill `openspec-batch-executor`, one lot at a time. At lot start, load **only** the skills the
   lot lists (once). Do the lot's **blocking first step** before any code.
3. **Inside a lot** — skill `tdd-workflow`: write failing test → run (see it fail for the right reason) →
   minimal code → run → refactor. A test that passes first time, or that guards a filter / threshold /
   privacy rule / allowlist, goes through `mutation-verified-testing` (break the code, see red, restore).
   Any unexpected failure → `systematic-debugging` before touching code.
4. **End of lot** — gate (§1) with real numbers, tick `tasks.md`, `graphify update .`, then skill `commit`
   (Conventional Commits, stage files by name, ask before committing). Propose `/compact` every 2 lots.
5. **Close the change** — skill `openspec-archive-change` (or `openspec archive <change>`), then update
   `CLAUDE.md` "Statut" and commands lines if they changed.

Never: send an application, scrape a protected page, put secrets/PII in git, prompts or logs, change the LLM
effort between requests of the same kind.

### Skill map (project skills in `.claude/skills/` unless marked global)

| Skill | Used in |
|---|---|
| `openspec-propose`, `openspec-batch-executor`, `openspec-archive-change` | every change |
| `tdd-workflow`, `mutation-verified-testing`, `systematic-debugging` | every code lot |
| `clean-code` | C0 (conventions), refactor step of any lot over ~150 lines |
| `database-design` | C1 L1, C4 L1, C6 L1 |
| `prompt-engineering` | C1 L4, C5 L2, C5 L3 |
| `avoid-ai-writing` | every lot that writes French user text: C1 L5, C5 L2–L3, C6 L3, README in C0/C7 |
| `commit` | end of every lot |
| `long-run-delivery` | only if the user runs several lots unattended (`/goal`, overnight) |
| `claude-api` (global) | C1 L4, C5 L2 — before writing any Anthropic SDK code |
| `sveltekit`, `browser-proof`, `fixing-accessibility` (global) | C7 |
| `threat-modeling` (global) | C4 L2 (webhook exposed to internet) |

---

## 3. Architecture

### 3.1 Runtime

```
GitHub Actions cron (UTC, every hour :30, 05–19 UTC)        Vercel (Python fn)            Vercel (SvelteKit, C7)
  py -m denicheur run --mode auto                            api/telegram.py               web/  dashboard + /projet
   ├─ collect (sources due)                                   → denicheur.telegram.webhook   reads/writes Postgres
   ├─ normalize → dedupe → geo → prefilter                    buttons, commands, drafts
   ├─ score (LLM, capped)                                            │
   ├─ notify: instant alerts / daily digest / J+7 reminders          │
   └─ log row in `executions` ───────────► Neon Postgres ◄───────────┘
```

### 3.2 Final repository layout

```
denicheur/
├── .github/workflows/collecte.yml        # C1 L6
├── api/telegram.py                       # C4 L2 — thin Vercel handler
├── vercel.json                           # C4 L2
├── alembic.ini · migrations/             # C1 L1 (env.py reads DATABASE_URL)
├── config/
│   ├── recherches.yaml                   # committed, no secrets
│   └── villes_hors_zone.txt              # C1 L3 — cities that trigger "lieu à vérifier"
├── profile/
│   ├── profil.md                         # C0 — from spec §2, no PII, committed
│   ├── regles_ecriture.md · lettre_modele.md   # C5 L1 — human-supervised
│   └── cv_alternance.md · cv_stage.md    # C5 L1 — local only (gitignored)
├── scripts/
│   ├── make_fixture.py                   # C0 — ft_test_results.json → tests/fixtures/lba_search.json
│   └── compare_effort.py                 # C1 L4
├── src/denicheur/
│   ├── __init__.py · __main__.py         # CLI (argparse)
│   ├── config.py                         # Config (pydantic) from YAML + Secrets from env
│   ├── models.py                         # Offre, ScoreLLM, enums (pydantic)
│   ├── messages_fr.py                    # ALL French user-facing text + formatters
│   ├── http.py                           # get_json() with retry/backoff/429
│   ├── clock.py                          # paris_now(), is_daytime(), tz helpers
│   ├── sources/  __init__.py (SOURCES registry) · la_bonne_alternance.py · adzuna.py · email_alertes.py
│   │             · recherche_entreprises.py · csv_entreprises.py
│   ├── pipeline/ normalize.py · dedupe.py · geo.py · prefilter.py · run.py
│   ├── scoring/  prompts.py · llm.py (protocol + Anthropic impl + cost) · service.py
│   ├── redaction/ prompts.py · service.py · gmail_drafts.py        # C5
│   ├── telegram/ api.py · digest.py · webhook.py · commands.py     # webhook/commands: C4
│   ├── mail/     imap.py · parsers.py                              # C2
│   └── db/       base.py (engine/session) · tables.py · repo.py
├── tests/  fixtures/ (lba_search.json, emails/*.eml, adzuna_search.json, etiquettes.json) · test_*.py
├── web/                                  # C7 SvelteKit
├── pyproject.toml · .env.example · README.md (FR)
```

### 3.3 Module contracts (signatures are binding)

```python
# models.py
class Piste(StrEnum): STAGE = "stage"; ALTERNANCE = "alternance"; AUTRE = "autre"
class Offre(BaseModel):
    source: str; source_id: str; url: str
    titre: str; entreprise: str | None; commune: str | None
    lat: float | None; lon: float | None
    piste: Piste; duree_mois: int | None
    debut: date | None; debut_des_que_possible: bool = False
    niveau_diplome: str | None            # "6", "7", … (european level) or None
    description: str; publiee_le: datetime | None; expire_le: datetime | None
    # filled by pipeline:
    distance_km: float | None = None; lieu_a_verifier: bool = False; motif_rejet: str | None = None
class ScoreLLM(BaseModel):               # LLM structured output (spec §6)
    score: int  # 0..100, validated client-side
    type: Literal["stage", "alternance", "autre"]
    points_forts: list[str]; points_faibles: list[str]
    alerte: str | None; projet_a_citer: str; resume: str

# sources/<name>.py — same interface for every source
def collecter(config: Config, http: httpx.Client, now: datetime) -> list[Offre]: ...
# sources/__init__.py
SOURCES: dict[str, Callable[[Config, httpx.Client, datetime], list[Offre]]]

# http.py
def get_json(client: httpx.Client, url: str, *, params=None, headers=None,
             max_retries: int = 4, sleep=time.sleep) -> Any
#   429 → sleep(int(Retry-After) or 2**attempt); 5xx/timeout → sleep(2**attempt); 4xx → raise; JSON decoded.

# pipeline
def normaliser_texte(s: str | None) -> str          # lower, strip accents (unicodedata NFKD), drop "h/f", collapse spaces
def cle_dedup(o: Offre) -> str                      # sha256(norm(entreprise)|norm(titre)|norm(commune)) hex
def dedupliquer(offres: list[Offre], deja_vues_urls: set[str], deja_vues_cles: set[str]) -> list[Offre]
def haversine_km(lat1, lon1, lat2, lon2) -> float
def appliquer_geo(offres, config) -> list[Offre]    # sets distance_km; > rayon → motif "hors_zone"; unknown coords → lieu_a_verifier, kept
def prefiltrer(offres, config, now) -> list[Offre]  # sets motif_rejet on rejects; returns all (rejects stored for stats)

# scoring
class Scorer(Protocol):
    def scorer(self, offre: Offre, today: date) -> tuple[ScoreLLM, Usage]: ...   # Usage = (input, output, cache_write, cache_read)
def scorer_offres(session, offres, config, scorer, now) -> int   # skips already-scored, honors daily cap + monthly budget

# telegram/api.py
class TelegramAPI:  # __init__(token, http)
    def send_message(chat_id, text_html, keyboard=None) -> int  # returns message_id
    def answer_callback(callback_id, text=None); def edit_keyboard(chat_id, message_id, keyboard)
    def set_webhook(url, secret); def get_updates() -> list[dict]
```

### 3.4 Data model (first Alembic migration, C1 L1)

| Table | Columns (type) | Constraints / indexes |
|---|---|---|
| `offres` | id PK int · source str · source_id str · url str · cle_dedup str(64) · titre · entreprise? · commune? · lat? lon? float · distance_km? · lieu_a_verifier bool · piste str · duree_mois? int · debut? date · debut_des_que_possible bool · niveau_diplome? · description text · publiee_le? · expire_le? · motif_rejet? · vue_le datetime · notifiee_le? datetime | UNIQUE(source, source_id), UNIQUE(url), INDEX(cle_dedup) |
| `scores` | offre_id FK unique · piste · score int · points_forts JSON · points_faibles JSON · alerte? · projet_a_citer · resume · modele · effort · input_tokens · output_tokens · cache_read_tokens · cout_eur float · cree_le | one score per offer = the LLM cache |
| `candidatures` | id · offre_id? FK · entreprise_id? (FK added C6) · statut · envoyee_le? · rappel_le? · relance_le? · notes? · cree_le · maj_le | statut ∈ nouvelle, interessante, candidature_envoyee, relancee, entretien, refus, offre, sans_reponse, ignoree |
| `brouillons` | id · candidature_id FK · type (email, lettre, relance, spontanee) · contenu text · gmail_draft bool · cree_le | |
| `executions` | id · debut · fin? · mode · offres_collectees · offres_retenues · offres_scorees · offres_notifiees · erreurs JSON · cout_eur | |
| `parametres` | cle PK · valeur text | keys: `pause`, `dernier_digest` (date), `derniere_collecte_alternance`, `derniere_collecte_stage`, `derniere_collecte_emails`, `dernier_update_id` |
| `entreprises` (C6 migration) | id · siret unique · nom · naf · commune · lat? lon? · distance_km · site? · source · priorite int · contactee_le? | |

JSON columns: `sqlalchemy.JSON` (works on SQLite and Postgres). `db/base.py:make_engine(url)` rewrites
`postgres://`/`postgresql://` → `postgresql+psycopg://`. All writes go through `db/repo.py` functions (no raw
session use in pipeline code).

### 3.5 Config (`config/recherches.yaml`, loaded into pydantic `Config`)

```yaml
centre: { commune: "Mareil-Marly", insee: "78367", lat: 48.8800, lon: 2.0775 }
rayon_km: 25
inclure_teletravail_complet: false
niveau_vise: "6"                      # Bac+3
pistes:
  alternance: { romes: ["M1805","M1806","M1807"], duree_mois: [12,24], frequence_heures: 3 }
  stage:      { duree_mois: [5,6], debut: ["2027-01","2027-02"], frequence_heures: 24 }
mots_cles_titre: [developpeur, developpeuse, developer, dev, web, full stack, fullstack, front, back, logiciel,
                  software, data, ia, ai, llm, python, react, typescript, javascript, informatique]
mots_exclus: [senior, confirme, experimente, manager, lead, "3 ans d'experience", "5 ans d'experience"]
mots_bonus: [claude code, cursor, copilot]
age_max_jours: 30
score_min: 65
alerte_immediate_alternance_min: 80
digest_max_offres: 10
plage_alertes: ["08:00", "20:00"]
heure_digest: "08:30"
llm:
  modele: "claude-sonnet-5-5"
  scoring:  { effort: "low",    max_tokens: 2000 }   # adaptive thinking counts toward max_tokens: 800 risks truncation
  ecriture: { effort: "medium", max_tokens: 8000 }
  llm_max_appels_jour: 150
  llm_budget_mensuel_eur: 5.0
  prix_usd_par_mtok: { input: 2.0, output: 10.0, cache_write: 2.5, cache_read: 0.10 }
  taux_usd_eur: 0.92
```

Secrets (`.env` locally, GitHub Secrets / Vercel env in prod; `Secrets` dataclass reads `os.environ`, missing
optional key = source disabled with a log line, never a crash): `LBA_API_KEY`, `ANTHROPIC_API_KEY`,
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_WEBHOOK_SECRET`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`,
`DATABASE_URL` (default `sqlite:///denicheur.db`), `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `DASHBOARD_PASSWORD`,
optional `FT_CLIENT_ID`, `FT_CLIENT_SECRET`.

### 3.6 Pipeline logic (`pipeline/run.py: executer(mode, deps, now)`)

1. `paris = now.astimezone(ZoneInfo("Europe/Paris"))` (dependency `tzdata`, required on Windows).
2. Open `executions` row. If `parametres.pause == "1"`: still collect and score, skip all sending.
3. **Due sources** (state-driven, robust to cron delays/DST): alternance sources if
   `paris - derniere_collecte_alternance ≥ 3h` and 08:00 ≤ paris < 20:00; stage sources if last stage collect
   is not today; e-mail source on every run (C2). Each source in its own `try`: an error is appended to
   `executions.erreurs` and the run continues.
4. Normalize (inside the source) → `dedupliquer` against DB URLs/keys → `appliquer_geo` → `prefiltrer` →
   store **all** new offers (rejects keep `motif_rejet`, for `/stats` and the dashboard).
5. `scorer_offres` on retained offers without a score (cap: calls today < `llm_max_appels_jour`, month cost <
   budget). LLM refusal / invalid output → no score row, error logged, offer retried next run once (store
   nothing so it is retried; count the attempt toward the cap).
6. Notify:
   - **Instant alert**: piste = alternance, score ≥ 80, `notifiee_le` null, inside 08:00–20:00 → "🚨 Alternance"
     message; set `notifiee_le`.
   - **Digest**: if paris ≥ 08:30 and `dernier_digest` ≠ today → top `digest_max_offres` with score ≥ 65 and
     `notifiee_le` null, ordered by score desc; header + one message per offer; set `notifiee_le` and
     `dernier_digest`. Empty digest → one short "Rien de nouveau aujourd'hui" message.
   - **J+7 reminders** (C4): candidatures `candidature_envoyee`, `envoyee_le ≤ today-7`, `relance_le` null,
     `rappel_le` null → reminder message; set `rappel_le`.
7. Close `executions` row (counts, cost). On an uncaught exception: close row with error and send
   "⚠️ La collecte du jour a échoué : <type d'erreur>" (no stack, no secrets), then exit code 1.

Prefilter rules, in this order (first match = `motif_rejet`): `piste_autre` (contract neither stage nor
alternance) → `expiree` (`expire_le < now`) → `trop_ancienne` (`publiee_le < now - 30 days`) →
`mot_exclu:<mot>` (normalized title) → `mots_cles_absents` (no `mots_cles_titre` word in normalized title,
word-boundary match) → `teletravail_complet` (if excluded). Unknown location never rejects.

`lieu_a_verifier`: True when coordinates are missing **or** the normalized description contains, as a whole
word, a city from `config/villes_hors_zone.txt` (≈50 big French cities outside Île-de-France + Troyes) and
that city ≠ the offer's commune. `# shortcut: fixed city list; upgrade to geocoding the mentions if false
positives appear.`

### 3.7 LLM contract (verified against the `claude-api` skill, 2026-11)

```python
client = anthropic.Anthropic()                      # reads ANTHROPIC_API_KEY
resp = client.messages.parse(
    model=cfg.llm.modele,                            # "claude-sonnet-5-5"
    max_tokens=cfg.llm.scoring.max_tokens,
    output_config={"effort": cfg.llm.scoring.effort},  # "low" — never varies between scoring calls
    system=[{"type": "text", "text": SYSTEM_SCORING, "cache_control": {"type": "ephemeral"}}],
    messages=[{"role": "user", "content": user_message(offre, today)}],
    output_format=ScoreLLM,
)
if resp.stop_reason in ("refusal", "max_tokens"): -> treat as failure (no score row)
score = resp.parsed_output; usage = resp.usage   # input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens
```

- Do not send `thinking` (Sonnet 5.5 runs adaptive by default; `{"type":"disabled"}` is a 400), no
  `temperature`, no assistant prefill.
- `SYSTEM_SCORING` = rubric (spec §6) + track rules + `profile/profil.md`, **byte-stable**: no date, no IDs.
  Today's date goes in the user message. Check `cache_read_input_tokens > 0` on the 2nd call in the manual
  smoke test; if 0, the prefix is under the model minimum — acceptable, just note it.
- If `messages.parse` rejects `output_config` together with `output_format` in the installed SDK version,
  fall back to `messages.create(output_config={"effort": ..., "format": {"type": "json_schema", "schema": ...}})`
  then `ScoreLLM.model_validate_json(text)`.
- Optional (recommended by the skill for Sonnet 5.5): server-side refusal fallback
  `client.beta.messages.parse(..., betas=["server-side-fallback-2026-07-01"], fallbacks="default")`.
  Add it in C1 L4 only if the beta `parse` exists in the installed SDK; otherwise refusal = skipped offer.
- Cost (EUR) = (input·p_in + output·p_out + cache_write·p_cw + cache_read·p_cr)/1e6 · taux_usd_eur.
- Writing (C5) uses the same call with `cfg.llm.ecriture` (effort medium) and a separate system prompt.

### 3.8 Telegram contract

- Messages in HTML parse mode; every dynamic value goes through `html.escape`. One message per offer
  (limit 4096 chars; truncate `points_*` lists to 3 items). Sleep 1 s between sends.
- Offer format = handoff §7 example; built only in `messages_fr.format_offre(offre, score, alerte: bool)`.
  Distance shown as "(4 km)"; unknown → "📍 lieu à vérifier". Duration/start line: stage "6 mois · début
  février 2027"; alternance "12 mois · début : dès que possible".
- Inline keyboard (C4): `callback_data` ≤ 64 bytes: `p:<offre_id>` Je postule, `b:<offre_id>` Brouillon,
  `r:<offre_id>` Rappel J+7, `x:<offre_id>` Ignorer. In C1 messages are sent without keyboard.
- Allowlist: every update whose `chat.id` ≠ `TELEGRAM_CHAT_ID` is ignored (HTTP 200, no reply).
- Webhook: header `X-Telegram-Bot-Api-Secret-Token` must equal `TELEGRAM_WEBHOOK_SECRET` (compare with
  `hmac.compare_digest`), else 403. Duplicate `update_id` ≤ `dernier_update_id` → ignored.

### 3.9 Invariants (each guarded by a test, mutation-verified)

1. No PII in prompts: prompt builders read only `profile/profil.md` and the offer; a test asserts the built
   prompt contains none of the patterns: phone (`0\d[\s.]?\d{2}`…), `@` e-mail, "né le".
2. Idempotence: running `executer` twice on the same fixture sends each offer at most once and scores it once.
3. Allowlist on `chat_id`; webhook secret check.
4. LLM effort per request type is read from config, never overridden in code.
5. Nothing sends e-mail: no `smtplib` import anywhere (`grep` test in the suite).

---

## 4. Changes and lots

Each lot lists: **Skills** · **Blocking first step** · **Files** · **Logic/tests** · **Done when**.

### C0 — `bootstrap-projet` (handoff P0)

**Why:** empty repo; need a runnable, tested skeleton and the committed fixture.

**L1 — Skeleton.** Skills: `clean-code`, `commit`.
Blocking step: `py --version`, `git status` (`.gitignore` already modified: show diff, keep it).
Files: `pyproject.toml` (project `denicheur`, `requires-python = ">=3.12"`, src layout, deps §header,
dev extras `pytest ruff mypy`; ruff `line-length = 110`, `target-version = "py312"`, select `E,F,I,UP,B,SIM`;
pytest `testpaths = ["tests"]`, `pythonpath = ["src"]`), `src/denicheur/__init__.py`, `__main__.py` (argparse
with subcommand stubs that print "non implémenté"), `.env.example` (all keys §3.5, empty values),
`tests/test_smoke.py` (imports package). Add to `.gitignore`: `denicheur.db`, `.vercel/`, `web/.svelte-kit/`.
Install: `py -m pip install -e ".[dev]"`.
Done when: gate passes (1 test).

**L2 — Config, profile, fixture.** Skills: `tdd-workflow`.
Files: `config/recherches.yaml` (§3.5), `src/denicheur/config.py` (`load_config(path) -> Config`,
`load_secrets(env=os.environ) -> Secrets`), `profile/profil.md` (spec §2 verbatim content, no contacts),
`scripts/make_fixture.py` (reads `ft_test_results.json`, writes the first block with `ensure_ascii=False,
indent=1` to `tests/fixtures/lba_search.json`), run it once and commit the output.
Tests: config loads; invalid `rayon_km: -1` raises; `Secrets` with missing `ADZUNA_*` → `adzuna_enabled is False`;
fixture has 16 jobs and 150 recruiters.
Done when: gate passes; README updated (FR: install, `.env`, commands).

### C1 — `mvp-alternance-digest` (handoff P1–P6)

**Why:** the urgent goal: a daily French digest + instant alerts of scored alternance offers.

**L1 — Models + DB.** Skills: `database-design`, `tdd-workflow`.
Blocking step: none. Files: `models.py`, `db/base.py`, `db/tables.py`, `db/repo.py`, `alembic.ini`,
`migrations/` (`alembic init migrations`, `env.py` uses `make_engine(os.environ.get("DATABASE_URL", ...))`
and `target_metadata = tables.metadata`), first revision autogenerated, reviewed by hand.
CLI `init-db` = `alembic upgrade head`.
Tests (SQLite in `tmp_path`, migration applied via Alembic API): insert offer + score, read back; second
insert of the same `(source, source_id)` is a no-op returning the existing id; `repo.urls_connues()` /
`repo.cles_connues()`; `repo.appels_llm_aujourdhui(now)`, `repo.cout_mois(now)`; `parametres` get/set.
Done when: "insert and re-read an offer and a score" passes.

**L2 — Source La bonne alternance.** Skills: `tdd-workflow`, `mutation-verified-testing`.
Blocking step: load the fixture and print the distinct `partner_label`, `contract.type` values (expect
`Apprentissage`, `Professionnalisation`).
Files: `http.py`, `sources/la_bonne_alternance.py`, `sources/__init__.py`.
Logic: `GET https://api.apprentissage.beta.gouv.fr/api/job/v1/search` with `Authorization: Bearer
<LBA_API_KEY>`, params `latitude, longitude, radius=rayon_km, romes="M1805,M1806,M1807"`. Map: `source="lba"`,
`source_id=identifier.id`, `url=apply.url`, `titre=offer.title`, `entreprise=workplace.name or
workplace.legal_name or workplace.brand`, `lon, lat = location.geopoint.coordinates` (**lon first**),
`commune` = parsed from the end of `location.address` (text after the 5-digit postal code), piste =
alternance (any of Apprentissage/Professionnalisation), `duree_mois=contract.duration`,
`debut_des_que_possible = start_type == "des_que_possible"`, `debut = contract.start` date when
`precise_date`, `niveau_diplome = target_diploma.european`, `publiee_le/expire_le = offer.publication.*`.
Also `collecter_recruteurs(...) -> list[dict]` (used in C6). Throttle: ≤ 60 calls/min (single call per run
today; keep `get_json` 429 handling).
Tests: fixture via `MockTransport` → 16 `Offre`, 150 recruiters; ITIC has `lat≈48.8579, lon≈2.3923`,
`debut_des_que_possible=True`, `niveau_diplome="7"`; 429 with `Retry-After: 1` then 200 → succeeds, `sleep`
called with 1; 401 → raises without retry; missing key → source skipped with log.
Done when: fixture gives 16 offers and 150 recruiters.

**L3 — Dedupe, geo, prefilter.** Skills: `tdd-workflow`, `mutation-verified-testing`.
Blocking step: run the pipeline functions on the fixture in a scratch script and print the table of §0.
Files: `pipeline/normalize.py`, `dedupe.py`, `geo.py`, `prefilter.py`, `config/villes_hors_zone.txt`.
Tests (`now = 2026-11-16T09:00+01:00`): 16 → 10 after dedupe (URL) and the Wavestone pairs share
`cle_dedup`; haversine Mareil-Marly→Paris 20e ≈ 23.2 km (±0.3); an offer at 30 km → `hors_zone`; missing
coords → kept with `lieu_a_verifier`; final retained set = exactly ITIC + Woodoo; Capgemini motif
`mot_exclu:confirme`; MGEN and Wavestone motif `mots_cles_absents` (or `trop_ancienne` for the 5 old ones —
assert the exact motif per offer from the measured table); Woodoo `lieu_a_verifier=True`, ITIC False.
Mutation-verify: radius comparison, `confirme` exclusion, age rule.
Done when: the three named cases are explained by tests.

**L4 — LLM scoring.** Skills: `claude-api` (global), `prompt-engineering`, `tdd-workflow`,
`mutation-verified-testing`.
Blocking step: `py -c "import anthropic; print(anthropic.__version__)"`; check `messages.parse` accepts
`output_config` (see §3.7 fallback).
Files: `scoring/prompts.py` (French system prompt: role, rubric 40/20/15/15/10, track rules incl. Bac+3 vs
Bac+5 malus + alert, rhythm ≠ 1/2 → alerte not elimination, bonus `mots_bonus`, `projet_a_citer` must be one
of the profile projects, "n'invente rien", answer in French; `user_message(offre, today)` with title,
company, commune + distance, contract, duration, start, diploma, description truncated to 6 000 chars),
`scoring/llm.py` (`AnthropicScorer`, `Usage`, `cout_eur(usage, cfg)`), `scoring/service.py`,
`scripts/compare_effort.py` (reads `tests/fixtures/etiquettes.json` = list of `{offre: {...}, score_attendu}`;
runs low and medium; prints mean |Δ|, offers crossing 65, total cost; `--dry-run` uses the fake).
Tests (fake scorer): valid score stored with tokens and cost; second run makes 0 calls (cache); cap 1 →
only 1 call; budget reached → 0 calls; refusal → no row; `ScoreLLM` rejects score 120; PII invariant (§3.9.1)
on the built system+user prompt; effort passed = config value.
Human step (before freezing `low`): user labels ~20 offers in `etiquettes.json`, runs
`py scripts/compare_effort.py` (real calls, ≈0.40 $). If mean |Δ| > 10 or > 3 offers cross 65 → set
scoring effort to `medium` in config.
Done when: a fixture offer gets a valid score, is not re-scored on the 2nd run, compare script runs.

**L5 — Telegram send + messages.** Skills: `avoid-ai-writing`, `tdd-workflow`.
Blocking step: user created the bot (handoff §7) and filled `TELEGRAM_BOT_TOKEN`; run
`py -m denicheur setup-telegram` → prints `chat.id` from `getUpdates`.
Files: `telegram/api.py`, `messages_fr.py`, `telegram/digest.py`. CLI `digest [--test]` (`--test` sends one
fake offer).
Tests (MockTransport capturing requests): format of ITIC message matches a golden string (emoji lines,
"(23 km)", "dès que possible", "⚠️ Niveau demandé : Bac+5"); HTML escaping of `<script>` in title; digest
picks top 10 ≥ 65 sorted desc and sets `notifiee_le`; sending to another chat id impossible (API object
bound to `TELEGRAM_CHAT_ID`).
Done when: `py -m denicheur digest --test` delivers a message on the user's phone.

**L6 — `run` command, executions, GitHub Actions, Neon.** Skills: `tdd-workflow`, `systematic-debugging`.
Blocking step: user creates Neon DB, sets `DATABASE_URL`; `py -m denicheur init-db` against Neon succeeds.
Files: `pipeline/run.py`, `clock.py`, CLI `run --mode auto|alternance|stage|digest [--dry-run]`,
`.github/workflows/collecte.yml`:
```yaml
on:
  schedule: [{cron: "30 5-19 * * *"}]   # UTC; code decides what is due (Paris time, DST-safe)
  workflow_dispatch: {}
jobs:
  run:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    concurrency: { group: collecte, cancel-in-progress: false }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - run: pip install -e .
      - run: python -m denicheur init-db && python -m denicheur run --mode auto
        env: { DATABASE_URL: ${{ secrets.DATABASE_URL }}, LBA_API_KEY: ${{ secrets.LBA_API_KEY }}, ... all §3.5 }
```
Plus a `test` job on push/PR running the gate.
Tests: `executer` on fixture with fakes: one `executions` row with counts; at 07:00 Paris no digest; at 08:31
digest sent once, second call same day sends nothing (idempotence invariant); alternance not re-collected
within 3 h; Woodoo score 85 at 10:00 → instant "🚨 Alternance" alert, not repeated in the digest; source
raising → error recorded, run continues; uncaught error → failure message + exit 1; `pause=1` → no send.
Done when: a manual `workflow_dispatch` run produces a digest and one `executions` row in Neon.
Close C1: archive, update `CLAUDE.md` (Statut, commands: `py -m pip install -e ".[dev]"`, gate, `py -m
denicheur run`).

### C2 — `alertes-email` (spec phase 5, moved earlier)

**Why:** big sites (Indeed, WTTJ, LinkedIn, JobTeaser) are only reachable through the alerts the user receives.
**Prereq (human):** Gmail 2FA + app password; label `Denicheur` with a Gmail filter on the alert senders;
`GMAIL_USER`, `GMAIL_APP_PASSWORD` set; 2–3 real alert e-mails per sender exported as `.eml`, **anonymized**
(own address replaced) into `tests/fixtures/emails/`.

**L1 — IMAP reader.** Skills: `tdd-workflow`. Files: `mail/imap.py`:
`lire_alertes(user, password, since: date, imap_factory=imaplib.IMAP4_SSL) -> list[email.message.Message]`
(select `Denicheur` read-only, `SEARCH SINCE`, `FETCH (RFC822)`, `BODY.PEEK` so mails stay unread).
Tests with a fake IMAP object. Done when: fake returns parsed messages; no flag changes issued.

**L2 — Parsers + source.** Skills: `tdd-workflow`, `mutation-verified-testing`.
Blocking step: open each `.eml`, list the HTML blocks that hold one offer per sender.
Files: `mail/parsers.py` (one function per sender, keyed by `From` domain, stdlib `html.parser`; extract
title, company, city, link; strip tracking params from links for dedupe), `sources/email_alertes.py`
(`collecter` → `Offre(source="email:<site>", source_id=sha1(url_clean))`, piste from title words
"alternance|apprentissage|apprenti" → alternance, "stage|stagiaire" → stage, else autre; description = text of
the block; coordinates None → geocode `commune` via `api-adresse.data.gouv.fr/search/?q=<commune>&type=municipality&limit=1`
with an in-process cache; failure → `lieu_a_verifier`).
Tests: each fixture e-mail yields the expected count of offers; same offer in two e-mails → 1 after dedupe;
unknown sender → 0 offers + log. Done when: alert offers appear in a dry-run digest without duplicates.

### C3 — `source-adzuna-stage` (handoff P7)

**Why:** stage track has no official source. **Prereq:** `ADZUNA_APP_ID/KEY`.
**L1.** Skills: `tdd-workflow`, `mutation-verified-testing`.
Blocking step: one real call, save the JSON to `tests/fixtures/adzuna_search.json` (strip nothing secret: the
response holds none), print `count` and 3 titles; record quota headers if present.
Logic: `GET https://api.adzuna.com/v1/api/jobs/fr/search/1` params `app_id, app_key, what=<keyword> stage,
where="Mareil-Marly", distance=25, max_days_old=30, results_per_page=50, content-type=application/json`;
one call per stage keyword (≤ 10/day). Map `id, title, company.display_name, location.display_name,
latitude, longitude, redirect_url, created, description (truncated by Adzuna), contract_type`. Piste stage
if title/description contains "stage|stagiaire|internship", else alternance if "alternance|apprenti", else
autre. Duration parsed by regex `(\d)\s*mois` when present.
Tests on the fixture + MockTransport; 429 path. Done when: stage offers reach a dry-run digest.

### C4 — `bot-interactif` (handoff P8, spec phase 2 minus drafts)

**Why:** act on offers from Telegram; track applications; J+7 reminders.

**L1 — Tracking model.** Skills: `database-design`, `tdd-workflow`. `repo` functions:
`marquer(offre_id, statut)`, `candidatures_a_relancer(today)`, `stats()`. Status transitions allowed:
nouvelle→interessante→candidature_envoyee→relancee→{entretien, refus, offre, sans_reponse}; any → ignoree.
Invalid transition raises. Alembic revision only if columns change.

**L2 — Webhook.** Skills: `threat-modeling` (global), `tdd-workflow`, `mutation-verified-testing`.
Blocking step: deploy a hello-world `api/telegram.py` to Vercel and confirm it imports `denicheur` (verify how
the current Vercel Python runtime installs deps — `pyproject.toml` or `requirements.txt` — and set
`vercel.json` `functions["api/telegram.py"] = {"maxDuration": 60, "includeFiles": "src/**"}`; add
`sys.path` insert of `src` in the handler if needed). Record the answer in `design.md`.
Files: `api/telegram.py` (BaseHTTPRequestHandler `do_POST` → read body → `webhook.handle(headers, body,
deps)` → status code), `telegram/webhook.py`, `telegram/commands.py`, CLI `set-webhook <url>`.
Callbacks: `p` → candidature `candidature_envoyee`, `envoyee_le=today`, keyboard edited to show "✅ Envoyée";
`r` → `rappel` planned (J+7 handled by the run); `x` → `ignoree`; `b` → reply "Brouillon disponible à
l'étape C5" until C5. Always `answerCallbackQuery`.
Commands: `/aujourdhui`, `/stage`, `/alternance`, `/candidatures`, `/relances`, `/stats`, `/pause`,
`/reprendre`, `/config` (texts in `messages_fr.py`).
Tests: wrong secret → 403; foreign chat → 200 + no API call; duplicate update_id ignored; each callback and
command produces the expected DB change and message. Mutation-verify the two guards.
Done when: tapping "✅ Je postule" on the phone updates Neon.

**L3 — Buttons on sent offers + J+7.** Add the keyboard to digest/alerts; add reminder step 6 of §3.6.
Tests: reminder sent once at J+7, not at J+6, not twice. Done when: a back-dated candidature triggers one reminder.

### C5 — `brouillons-candidature` (handoff P9, spec §8)

**L1 — Writing profile (human-supervised, no code).** Skills: `avoid-ai-writing`.
Blocking step: user grants read access to `CV_base/` (currently denied in `.claude/settings.json`) and starts
Claude with `--add-dir "C:\Users\era92\Desktop\Matteo\lettres motivation taf"`. Follow handoff §10 prompts
exactly; **show the diff before saving**; style only, no names/addresses copied. Outputs:
`profile/regles_ecriture.md`, `profile/lettre_modele.md` (placeholders `{entreprise}`, `{poste}`, `{projet}`,
`{detail}`), local-only `profile/cv_alternance.md`, `profile/cv_stage.md`. Verify `git status` does not list
`cv_*.md`.

**L2 — Draft service.** Skills: `claude-api`, `prompt-engineering`, `avoid-ai-writing`, `tdd-workflow`.
Files: `redaction/prompts.py` (system = `regles_ecriture.md` + `lettre_modele.md` + `profil.md`, stable;
user = offer + chosen project + track availability sentence), `redaction/service.py`
`rediger(offre, score, type: Literal["email","lettre","relance","spontanee"]) -> str` using `llm.ecriture`
(effort medium, never changed). Output must end with a line "Éléments du profil utilisés : …" (handoff §10)
so the user can verify; length checks: email 120–180 words, lettre 250–300 (one retry if out of range,
then send anyway with a ⚠️ note). Unknown company detail → literal `[à compléter : détail sur l'entreprise]`,
never invented.
Tests (fake LLM): prompt has no PII; word-count retry path; placeholder kept when no detail.
**L3 — Wire to Telegram + Gmail drafts.** Files: `redaction/gmail_drafts.py`
(`creer_brouillon(subject, body, to="")` → IMAP `APPEND "[Gmail]/Drafts" (\Draft)` with a `email.message
.EmailMessage`); callback `b:` → answer "⏳ Rédaction…", generate, store in `brouillons`, send text to
Telegram + "📥 Créer le brouillon Gmail" button (`g:<brouillon_id>`); reminder message gets a "✉️ Relance"
button (one relance max: second request refused with a message).
Tests: fake IMAP receives exactly one APPEND to Drafts, never a send; invariant §3.9.5 (no smtplib).
Done when: tapping "✉️ Brouillon" returns a relevant French draft in < 30 s (measure, report the time).

### C6 — `candidatures-spontanees` (spec phase 4)

**L1 — Companies table + import.** Skills: `database-design`, `tdd-workflow`. Alembic revision adding
`entreprises` and `candidatures.entreprise_id`. Import `entreprises_spontanees_mareil-marly.csv`
(`encoding="utf-8-sig"`, `delimiter=";"`, `rang`→priorite, `siret` unique) and LBA recruiters
(`collecter_recruteurs`) — upsert by siret.
**L2 — Recherche d'entreprises.** Blocking step: one real call to
`https://recherche-entreprises.api.gouv.fr/near_point?lat=48.88&long=2.0775&radius=25&activite_principale=62.01Z`
(verify endpoint/params in the API docs; it was down on 2026-11-16 — if still down, skip the lot and say so).
Upsert results (NAF 62.01Z, 62.02A, 58.29C, 63.11Z; effectif PME).
**L3 — Daily list.** Skills: `avoid-ai-writing`, `tdd-workflow`. In the digest run (once/day): 10 companies
not contacted, order priorite then distance; one message each with "✉️ Brouillon spontané" (`s:<id>`) and
"❌ Ignorer". Cap: ≤ 15 drafts/day; one message per company (`contactee_le` set when user taps "✅ Envoyée").
Tests: cap, never twice the same company. Done when: a list of 10 companies arrives with working draft buttons.

### C7 — `dashboard` (spec phase 3)

Skills: `sveltekit`, `browser-proof`, `fixing-accessibility` (global), `avoid-ai-writing`, `tdd-workflow`.
**L1 — Scaffold + auth.** `web/` via `npx sv create web` (TypeScript, minimal), `postgres` npm client,
`src/lib/server/db.ts` (reads `DATABASE_URL`), `hooks.server.ts`: every route except `/projet` and `/login`
requires a cookie set after comparing `DASHBOARD_PASSWORD` (timing-safe) → httpOnly, secure, sameSite=strict.
**L2 — Kanban + filters.** `/` columns by statut; card = offre titre/entreprise/score/distance; form action
to change statut (same transition rules as C4 L1 — duplicate the list in `src/lib/statuts.ts` and add a Python
test that compares both lists to avoid drift); filters stage/alternance; offers below threshold listed in
`/offres`.
**L3 — Stats + portfolio page.** `/stats` (offres vues, retenues, scorées, candidatures, réponses, coût du
mois from `executions`); `/projet` public page (FR) describing the architecture, no personal data. README FR
with screenshots of bot and dashboard. Verify with `browser-proof` (real browser: login, move a card, stats).
Done when: all applications are visible and editable from the dashboard.

---

## 5. Human prerequisites (Claude cannot do these)

| Before | Action |
|---|---|
| C1 L4 | `ANTHROPIC_API_KEY` in `.env`; label ~20 offers for `etiquettes.json` |
| C1 L5 | Create bot via @BotFather, `/start` it |
| C1 L6 | Neon project + `DATABASE_URL`; GitHub repo **private** + secrets; regenerate the francetravail.io secret (handoff §11) |
| C2 | Gmail 2FA + app password, label + filter, anonymized `.eml` samples; alerts created on Indeed/WTTJ/LinkedIn/JobTeaser |
| C3 | Adzuna developer keys |
| C4 | Vercel account/project, `TELEGRAM_WEBHOOK_SECRET` |
| C5 L1 | Grant access to `CV_base/` and the letters folder, review diffs |
| C7 | Second Vercel project (root `web/`), `DASHBOARD_PASSWORD` |

---

## 6. Verification

- **Per lot:** the gate (§1) with counts; `openspec validate <change>`; mutation-verified guard tests.
- **C1 end-to-end:** `py -m denicheur run --mode auto --dry-run` locally on the fixture prints 2 retained
  offers (ITIC, Woodoo with "lieu à vérifier"); then a `workflow_dispatch` run on GitHub → digest on the phone
  + one `executions` row in Neon; run it again → nothing re-sent.
- **C4/C5:** tap each button on the phone; draft arrives < 30 s; Gmail shows a draft, nothing in "Sent".
- **C7:** `browser-proof` session: login, move a card, see it in Telegram `/candidatures`.
- **Cost:** after one week, `SELECT sum(cout_eur) FROM executions` ≤ 5 € pro rata.

## 7. First actions after this plan is approved

1. Copy this file to `docs/plans/2026-11-16-denicheur-roadmap.md` (writing-plans convention) and commit it.
2. Fill `openspec/config.yaml` `context:` with 5 lines: French user-facing text / English code; never send
   applications; no PII to LLM or git; tests offline with fixtures; plan file path above is authoritative.
3. Switch to Sonnet 5.5 medium and start with: `/openspec-propose bootstrap-projet` using §4 C0.
