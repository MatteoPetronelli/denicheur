# Dénicheur — Handoff per Claude Code

Documento di passaggio per continuare lo sviluppo con Claude Code.
Aggiornato al **16 novembre 2026**. Da leggere insieme a `Denicheur-specifications.md` (specifiche complete).

> **Regola d'oro**: lo sviluppo si fa a passi piccoli. Ogni richiesta a Claude Code deve avere un obiettivo, i file coinvolti e un criterio "fatto quando". Sotto trovi i prompt già pronti (§9).

---

## 1. Cos'è e perché

Strumento personale che cerca **alternanza (urgente)** e **stage**, valuta le offerte con un LLM rispetto al profilo di Matteo e manda su **Telegram** (in francese) un digest e le offerte migliori. Prepara bozze di candidatura e di CV/lettera in francese. **L'invio finale è sempre umano.**

| Obiettivo | Dettaglio |
|---|---|
| **Alternanza** (priorità 1, urgente) | 1–2 anni, ritmo 1 settimana scuola / 2 settimane in azienda (già validato con la scuola). Inizio **appena possibile**, anche "domani". |
| **Stage** (priorità 2) | 5–6 mesi, inizio gennaio 2027, febbraio al più tardi. |
| **Zona** | Raggio **25 km** da Mareil-Marly (78750). Comune INSEE **78367**, lat **48.8800**, lon **2.0775**. |
| **Lingua** | Tutto ciò che l'app mostra (Telegram, bozze, dashboard) è in **francese**. Codice e identificatori in inglese. |

**Domanda ancora aperta**: quale diploma prepara l'alternanza (Bachelor 3 = Bac+3, oppure Mastère = Bac+5)? Se è un Mastère, le offerte con livello "Bac+5" sono quelle giuste. Il filtro `target_diploma_level` va impostato di conseguenza (§6).

---

## 2. Cosa è stato fatto

File già prodotti (nella cartella `D:\Matteo\denicheur`, Git Bash / `py` su Windows):

| File | Contenuto |
|---|---|
| `Denicheur-specifications.md` | Specifiche complete: pipeline, scoring, Telegram, dati, roadmap |
| `test_france_travail.py` | Script di test delle API (4 test). Lancio: `py test_france_travail.py`. Variabili: `FT_CLIENT_ID`, `FT_CLIENT_SECRET`, `LBA_API_KEY`, `FT_TEST=offres\|lbb\|entreprises\|alternance` |
| `ft_test_results.json` | Risultati reali del test 4 (offerte e aziende). **Usalo come fixture per i test.** |
| `entreprises_spontanees_mareil-marly.csv` | 150 aziende IT entro ~11 km, ordinate per priorità, con link ufficiale di candidatura spontanea |

---

## 3. Stato delle API (verificato sul computer di Matteo)

| API | Stato | Note |
|---|---|---|
| **La bonne alternance** — `GET https://api.apprentissage.beta.gouv.fr/api/job/v1/search` | **Funziona** | Chiave API gratuita (account sul sito, chiave *production*, sola lettura). Header `Authorization: Bearer <chiave>`. Limite **60 chiamate/min**. Max **150 risultati per fonte**. Uso solo **non lucrativo**. |
| **France Travail — Offres d'emploi v2** | **Non accessibile** | Token rifiutato con `invalid_scope` (3 varianti di scope provate). L'API non compare nel catalogo dell'applicazione di Matteo. Da chiedere al supporto francetravail.io. |
| **France Travail — La Bonne Boite v2** | **Accesso condizionato** | Token valido con `api_labonneboitev2`, ma `GET /recherche` risponde `403 Invalid scope`: serve un'abilitazione. Non bloccante (vedi §5). |
| **Recherche d'entreprises** (`recherche-entreprises.api.gouv.fr`) | **Non verificato** | Il test ha dato timeout/503: probabile disservizio temporaneo di data.gouv.fr. Riprovare più tardi. |
| **geo.api.gouv.fr** | Instabile | Due timeout. Il fallback `api-adresse.data.gouv.fr` funziona (già nello script). |
| **Adzuna** | **Non provato** | Chiave gratuita su developer.adzuna.com. Serve per gli **stage** (nessuna fonte ufficiale copre bene gli stage). |

### Cosa è emerso dai dati reali (test 4)
- Con ROME `M1805,M1806,M1807` entro 25 km: **16 offerte, solo 10 URL distinti**. Quasi tutte sono rumore:
  - 12 sono 6 annunci **Wavestone** "Stage de fin d'études / Alternance" (consulenza) duplicati e classificati male come sviluppo.
  - **Woodoo** "Full Stack" risulta a Parigi (sede), ma il testo dice **La Chapelle-Saint-Luc (Troyes)**.
  - **Capgemini** "Data Business Analyste" ha una descrizione per un profilo HR di scuola di commercio.
  - Unico annuncio pulito: **ITIC Paris / Synacktiv** (sviluppatore sicurezza, `des_que_possible`, 6 mesi, Parigi 20°, diploma target Bac+5).
- Le **aziende spontanee** (`recruiters`) sono 150, tutte entro ~11 km, quasi tutte IT (NAF 62.02A, 62.01Z, 58.29C, 63.11Z). **Non hanno sito web né email** nei dati.
- **Conclusione**: l'API da sola vede poche offerte di sviluppo. I grandi siti (Indeed, Welcome to the Jungle, LinkedIn) non sono coperti. Per questo le email di avviso e le candidature spontanee sono centrali.

### Struttura della risposta LBA (per il parser)
```text
jobs[]:
  identifier.{id, partner_label, partner_job_id}      # partner_label: offres_emploi_lba | France Travail | Hellowork | ...
  workplace.{name, legal_name, siret, size, website,
             location.address, location.geopoint.coordinates [LON, LAT],   # attenzione: ordine lon, lat
             domain.naf.{code,label}}
  contract.{start, start_type, start_is_flexible, duration, type[], remote}  # start_type: des_que_possible | precise_date
  offer.{title, description, rome_codes[], target_diploma{european,label}|null, desired_skills[]}
  apply.{url, phone, recipient_id}
recruiters[]:                                          # aziende per candidatura spontanea
  identifier.id, workplace.{...come sopra}, apply.url  # apply.url = pagina ufficiale LBA per candidarsi
```

### Trappole note (da gestire nel codice)
1. **Duplicati**: stesso `apply.url` ripetuto → deduplicare per URL e per (azienda, titolo normalizzato).
2. **Posizione ingannevole**: la distanza usa la sede dell'azienda, non il luogo di lavoro (caso Woodoo). Cercare nel testo città diverse e marcare "luogo da verificare".
3. **Classificazione ROME sporca** sulle offerte France Travail: filtrare per parole chiave nel titolo (developer, développeur, web, full stack, data, IA, etc.) oltre al ROME.
4. **`target_diploma` quasi sempre null** (13 su 16): il filtro per livello include i "non precisati".
5. **Rate limit**: rispettare `retry-after` su 429; LBA 60/min; France Travail 10/s.

---

## 4. Decisioni prese

- **Linguaggio**: Python 3.12+ (httpx, pydantic, SQLAlchemy, pytest, ruff).
- **Fase 1 locale con SQLite**, accesso al DB dietro SQLAlchemy così da passare a **Postgres** (Neon o Supabase, tier gratuito) quando servirà il webhook Telegram (fase 2).
- **Esecuzione**: prima `py -m denicheur run` in locale, poi **GitHub Actions** (cron). L'alternanza gira ogni 3 ore in giornata, lo stage una volta al giorno. Gli schedule di GitHub sono in **UTC** e possono ritardare.
- **LLM**: un solo modello per tutto, **Claude Sonnet 5.5** (ID API `claude-sonnet-5-5`), con livelli di *effort* diversi per compito:
  - **Punteggio delle offerte → `effort: low`**. È classificazione con output JSON strutturato, ripetuta su molte offerte: serve velocità e costo basso. Il livello low riduce i token a costo di un po' di qualità, quindi va verificato (vedi sotto).
  - **Bozze di candidatura, lettere, varianti di CV → `effort: medium`**. Qui conta la qualità della scrittura in francese, ma non serve il livello massimo.
  - Si imposta con `output_config={"effort": "low"}` (o `"medium"`) nella richiesta Messages. Valori possibili: low, medium, high, xhigh, max; il predefinito dell'API è high. **Verifica nella pagina "Effort" della documentazione che Sonnet 5.5 sia tra i modelli supportati.**
  - **Non cambiare l'effort tra richieste dello stesso tipo**: cambiarlo invalida la cache dei prefissi. Quindi punteggio sempre `low`, scrittura sempre `medium`, in chiamate separate.
  - **Prima di fissare `low`**: confronta `low` e `medium` su ~20 offerte etichettate a mano (vedi P4). Se i punteggi divergono troppo, passa a `medium` anche per il punteggio.
  - Tetto di chiamate al giorno e cache per offerta.
- **Telegram**: solo invio nella fase 1; bottoni e comandi (webhook su Vercel) nella fase 2.
- **Nessuno scraping aggirando protezioni, nessun bypass CAPTCHA, nessun invio automatico di candidature.**

---

## 5. Fonti: priorità aggiornata

1. **La bonne alternance** (offerte + `recruiters`) — funziona, base della pista alternanza.
2. **Aziende spontanee**: partire dal CSV; arricchire (sito, contatto) in modo assistito. API Recherche d'entreprises quando torna online.
3. **Email di avviso** di Indeed, Welcome to the Jungle, LinkedIn, JobTeaser, **lette tramite Gmail** (§8). È la via per vedere le offerte dei grandi siti senza scraping.
4. **Adzuna** per gli stage.
5. France Travail Offres v2 e La Bonne Boite v2, **solo se arriva l'abilitazione**.

### Messaggio pronto per il supporto francetravail.io ("Nous contacter")
```text
Bonjour,
Je développe un outil personnel et non commercial de recherche de stage et d'alternance (Bachelor Informatique).
1) Mon application (identifiant client commençant par PAR_denicheur) n'a pas accès à l'API « Offres d'emploi v2 » :
   le jeton est refusé avec invalid_scope. Cette API est-elle accessible aux particuliers et comment l'ajouter ?
2) Pour « La Bonne Boite v2 », le jeton est délivré (scope api_labonneboitev2) mais GET /recherche renvoie 403 « Invalid scope ».
   Une habilitation est-elle nécessaire, et comment la demander ?
Merci d'avance. Cordialement, Matteo Petronelli
```

---

## 6. Configurazione (esempio)

```yaml
# config/recherches.yaml
centre: { commune: "Mareil-Marly", insee: "78367", lat: 48.8800, lon: 2.0775 }
rayon_km: 25
pistes:
  alternance:
    prioritaire: true
    romes: ["M1805", "M1806", "M1807"]   # da ampliare: data, IA, sistemi (da verificare)
    target_diploma_level: null            # 6 = Bac+3, 7 = Bac+5 -> DA DECIDERE (domanda aperta §1)
    duree_mois: [12, 24]
    rythme: "1 semaine école / 2 semaines entreprise"
    debut: "des_que_possible"
    frequence_heures: 3
  stage:
    duree_mois: [5, 6]
    debut: ["2027-01", "2027-02"]
    frequence_heures: 24
score_min: 65
alerte_immediate_alternance_min: 80
llm_max_appels_jour: 150
llm:
  modele: "claude-sonnet-5-5"          # Claude Sonnet 5.5
  scoring:  { effort: "low",    max_tokens: 800 }    # classificazione JSON, alto volume
  ecriture: { effort: "medium", max_tokens: 2000 }   # bozze, lettere, varianti CV
```

Variabili d'ambiente (`.env`, **mai nel repository**):
`LBA_API_KEY`, `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `DATABASE_URL`, e solo se arrivano gli accessi: `FT_CLIENT_ID`, `FT_CLIENT_SECRET`.

---

## 7. Telegram (francese)

### Creare il bot
1. Su Telegram apri **@BotFather**, comando `/newbot`, scegli nome e username. Copia il **token** in `.env` (`TELEGRAM_BOT_TOKEN`).
2. Scrivi `/start` al tuo bot, poi apri `https://api.telegram.org/bot<TOKEN>/getUpdates` e leggi `message.chat.id`. Mettilo in `TELEGRAM_CHAT_ID`.
3. **Il bot risponde solo a quel `chat_id`**. Qualsiasi altro utente viene ignorato.

### Messaggi (esempio)
```text
🚨 Alternance · Développeur Full Stack
🏢 Exemple SAS · 📍 Chatou (6 km)
🕒 12 mois · début : dès que possible
⭐ Score 86/100
✅ React/TypeScript, Python
⚠️ Niveau demandé : Bac+5
💡 Projet à citer : RiftMind
🔗 Voir l'offre
[✅ Je postule] [✉️ Brouillon] [🔔 Rappel J+7] [❌ Ignorer]
```
Testi centralizzati in `messages_fr.py`. Fase 1: invio semplice. Fase 2: bottoni e comandi (`/aujourdhui`, `/alternance`, `/stage`, `/candidatures`, `/relances`, `/stats`, `/pause`, `/reprendre`, `/config`) con webhook e `secret_token`.

---

## 8. Gmail (MCP) per leggere gli avvisi e preparare le proposte

**Principio: Gmail serve a leggere e a creare bozze. L'invio resta una scelta esplicita di Matteo.**

- **Collegamento**: in Claude Code usa `/mcp` per vedere se il connettore Gmail dell'account Claude è disponibile. Altrimenti si può usare un MCP Gmail di terzi: in quel caso verificare i permessi richiesti (scegliere il minimo: lettura + creazione di bozze) e leggere il codice.
- **Lettura**: filtrare le email di avviso (mittenti Indeed, Welcome to the Jungle, LinkedIn, JobTeaser) con un'etichetta Gmail dedicata, per esempio `Denicheur`, e leggere solo quella. Estrarre titolo, azienda, luogo, link e passare il tutto alla stessa pipeline di punteggio.
- **Scrittura**: creare **bozze** in Gmail con oggetto e testo in francese, destinatario vuoto o da confermare. Matteo rilegge e invia.
- **Se si vuole l'invio dal bot**: solo dopo un tocco su "Envoyer" in Telegram, **un messaggio alla volta**, con tetto giornaliero (10–15) e un solo messaggio per azienda. Mai invio in blocco.
- **Dati personali**: non mettere negli argomenti di ricerca o nei log indirizzi, telefono o data di nascita.

---

## 9. Prompt pronti per Claude Code (uno alla volta)

Prima di tutto, apri Claude Code nella cartella del progetto e di' che deve leggere `handoff.md` e `Denicheur-specifications.md`.

**P0 — Bootstrap**
```text
Leggi handoff.md e Denicheur-specifications.md. Crea la struttura del repository come nella sezione 12 della specifica:
pyproject.toml (Python 3.12, httpx, pydantic, SQLAlchemy, pytest, ruff), .gitignore (con .env, *.db, ft_test_results.json, CV_base/),
.env.example (senza valori), README.md in francese, cartelle src/denicheur, tests, config, profile.
La cartella CV_base/ esiste già nel repository (la crea Matteo): non toccarla e non committarla.
Non committare mai segreti. Fatto quando: `py -m pytest` e `ruff check` passano a vuoto.
```

**P1 — Modello e database**
```text
Crea il modello Offre (pydantic) e le tabelle SQLAlchemy offres, scores, candidatures, executions (sezione 11 della specifica) con SQLite.
Il DB è dietro un'interfaccia così da passare a Postgres dopo. Scrivi i test.
Fatto quando: inserisco e rileggo un'offerta e un punteggio, test passanti.
```

**P2 — Sorgente La bonne alternance**
```text
Implementa src/denicheur/sources/la_bonne_alternance.py con collecter(config) -> list[Offre] e collecter_recruteurs(config).
Usa la struttura di risposta descritta in handoff.md §3 e ft_test_results.json come fixture di test (nessuna chiamata di rete nei test).
Gestisci: coordinate [lon, lat], rate limit 60/min con retry-after, chiave da LBA_API_KEY.
Fatto quando: i test sulla fixture restituiscono 16 offerte e 150 aziende.
```

**P3 — Pulizia e filtri**
```text
Implementa pipeline/dedupe.py, geo.py (haversine, rayon_km=25 da config), prefilter.py.
Dedup per apply.url e per (azienda, titolo normalizzato). Se la descrizione cita una città diversa dalla sede, marca "lieu à vérifier".
Prefiltro per parole chiave (developer/développeur/web/full stack/data/IA) e parole escluse (senior, confirmé, "fin d'études" se non è alternanza).
Fatto quando: sulla fixture le 16 offerte diventano pochi risultati puliti e i casi Wavestone, Woodoo, Capgemini sono spiegati nei test.
```

**P4 — Scoring con LLM**
```text
Implementa scoring/ con prompt in francese, output JSON validato pydantic (score, points_forts, points_faibles, alerte, projet_a_citer, resume),
modello e livello di effort letti da config (llm.modele = claude-sonnet-5-5, llm.scoring.effort = low, passato come output_config={"effort": ...}),
tetto llm_max_appels_jour, cache per offerta. Usa profile/profil.md (senza dati personali). Barème nella specifica §6.
Non cambiare l'effort tra una richiesta e l'altra di questo tipo.
Aggiungi uno script scripts/compare_effort.py che, su un file di ~20 offerte etichettate a mano (tests/fixtures/etichette.json), confronta i punteggi con effort low e medium
e stampa differenza media, offerte che cambiano soglia (65) e costo stimato. Test con client simulato.
Fatto quando: un'offerta della fixture riceve un punteggio valido, non viene ricalcolata alla seconda esecuzione e lo script di confronto gira.
```

**P5 — Digest Telegram (solo invio)**
```text
Implementa telegram/notifier.py: invio del digest in francese (messages_fr.py), formattazione come nell'esempio di handoff.md §7,
comando di setup per ricavare il chat_id. Solo TELEGRAM_CHAT_ID autorizzato. Fatto quando: `py -m denicheur digest` manda un messaggio di prova.
```

**P6 — Comando unico e pianificazione**
```text
Crea `py -m denicheur run` (collect → dedupe → filtri → scoring → notifica) e .github/workflows/collecte.yml (cron ogni 3 ore in giornata, UTC, con workflow_dispatch).
Notifica Telegram se l'esecuzione fallisce. Fatto quando: una esecuzione manuale produce un digest e registra una riga in executions.
```

**P7 — Adzuna (stage)**, **P8 — Bot interattivo (webhook Vercel + Postgres)**, **P9 — Bozze e Gmail (solo bozze)**: fare solo dopo P0–P6, riusando la stessa struttura. Per P9: "crea una bozza Gmail in francese per l'offerta X partendo dal profilo e dal modello di lettera; non inviare mai". La scrittura usa Claude Sonnet 5.5 con `effort: medium` (config `llm.ecriture`).

### Richieste utili durante lo sviluppo
```text
Mostrami il diff prima di scrivere i file.        Aggiungi un test che riproduce questo errore: <errore>.
Spiega in 5 righe cosa fa questo modulo.          Non toccare i file in profile/ senza chiedermelo.
```

---

## 10. CV e lettera di motivazione

### Dove sono i file di partenza

| Cosa | Dove | Note |
|---|---|---|
| I 2 CV base (alternanza e stage) | `CV_base/` nella radice del repository (la crea Matteo) | Contengono dati personali: **cartella in `.gitignore`, mai su git**. Formato libero (PDF, DOCX o MD). |
| Lettere di motivazione di esempio | `C:\Users\era92\Desktop\Matteo\lettres motivation taf` (**fuori dal repository**) | Sola lettura. Il percorso ha spazi: va tra virgolette. |

**Come deve usarli Claude Code**
- **CV_base/**: elenca i file della cartella e cerca quello per l'alternanza e quello per lo stage dal nome. Se non è chiaro quale sia quale, chiedi. Se sono PDF o DOCX, estrai il testo in Markdown per creare `profile/cv_alternance.md` e `profile/cv_stage.md`. L'originale non si modifica.
- **Lettere di esempio**: leggi tutti i file della cartella (`.docx`, `.pdf`, `.md`, `.txt`) e ricava **solo lo stile**: struttura, apertura e chiusura, tono, lunghezza, formule ricorrenti. Con questo scrivi `profile/regles_ecriture.md` e `profile/lettre_modele.md` con segnaposto `{entreprise}`, `{poste}`, `{projet}`, `{detail}`.
- **Non copiare** nel repository le lettere né i nomi di aziende, indirizzi, nomi di recruiter o altri dati personali che contengono. Il modello deve essere generico.
- Se Claude Code non riesce a leggere quel percorso (si trova fuori dalla cartella del progetto), avvialo con `claude --add-dir "C:\Users\era92\Desktop\Matteo\lettres motivation taf"` oppure autorizza l'accesso quando lo chiede.

**Fonte unica di verità per il codice**: i file markdown modificabili in `profile/`. I CV originali restano in `CV_base/`.

```text
CV_base/                    # i 2 CV originali (solo locale, in .gitignore)
├── <CV alternance>.pdf|docx|md
└── <CV stage>.pdf|docx|md

profile/
├── profil.md              # competenze, progetti, esperienze (SENZA contatti) → usato dal punteggio
├── cv_alternance.md       # da CV_base: "Recherche d'alternance — rythme 1 semaine école / 2 semaines entreprise — début dès que possible"
├── cv_stage.md            # da CV_base: "Recherche de stage 5–6 mois, janvier/février 2027"
├── lettre_modele.md       # lettera con segnaposto {entreprise}, {poste}, {projet}, {detail}, derivata dalle lettere di esempio
└── regles_ecriture.md     # tono, lunghezza, vouvoiement, cosa non inventare, stile ricavato dalle lettere di esempio
```

`cv_alternance.md` e `cv_stage.md` contengono i contatti, quindi sono solo locali: aggiungi anche `profile/cv_*.md` al `.gitignore`. `profil.md` non ha contatti e può stare su git.

**Cose da correggere nel CV attuale per l'alternanza** (suggerimenti, decide Matteo):
- Il titolo dice "Recherche de stage (5 à 6 mois)": per l'alternanza serve una variante separata.
- Indicare il ritmo di alternanza e la disponibilità immediata.
- Ordinare i progetti in base all'offerta (IA/LLM per profili IA, SvelteKit/React per il web).

**Regole per le lettere**
- Basarsi solo su `profil.md` e sull'offerta. **Mai inventare** competenze, date, esperienze.
- Un progetto concreto e un dettaglio specifico dell'azienda (sito, stack, blog).
- 120–180 parole per l'email, 250–300 per la lettera. Vouvoiement.
- Per le candidature spontanee: un solo messaggio per azienda, personalizzato.

**Prompt esempio**
```text
Leggi la cartella CV_base/ e identifica il CV per l'alternanza e quello per lo stage (chiedimi se non è chiaro).
Estrai il testo e crea profile/cv_alternance.md e profile/cv_stage.md: nel CV alternance cambia il titolo in "Recherche d'alternance",
aggiungi ritmo (1 settimana scuola / 2 settimane azienda) e disponibilità immediata. Non inventare nulla. Mostrami il diff prima di salvare.
```
```text
Leggi tutte le lettere in "C:\Users\era92\Desktop\Matteo\lettres motivation taf" (sola lettura). Ricava lo stile: struttura, tono, lunghezza,
formule ricorrenti. Scrivi profile/regles_ecriture.md e profile/lettre_modele.md con segnaposto {entreprise}, {poste}, {projet}, {detail}.
Non copiare nomi di aziende, indirizzi o dati personali. Mostrami il diff prima di salvare.
```
```text
Scrivi una lettera in francese per questa offerta: <incolla offerta>. Usa lettre_modele.md e il progetto più adatto.
Massimo 280 parole. Elenca in fondo cosa hai usato dal profilo, così posso verificarlo.
```

---

## 11. Sicurezza e regole

- **Rigenera la chiave segreta di francetravail.io**: il file con l'identificativo e la chiave è passato in chat. Salva la nuova chiave solo in `.env` o nei segreti di GitHub.
- `.env`, database, `ft_test_results.json`, `CV_base/` e `profile/cv_*.md` **fuori da git**. Le lettere di esempio restano nella cartella sul Desktop, fuori dal repository. Repository **privato**.
- Telegram: allowlist su `chat_id`. Gmail: permessi minimi, bozze di default, niente invii in blocco.
- Rispetta i limiti di ogni API e i termini d'uso (LBA: uso non lucrativo). Niente bypass di CAPTCHA, niente scraping di pagine protette.
- Non inviare al LLM telefono, data di nascita o indirizzo.

---

## 12. Prossimi passi (in ordine)

1. Decidere il diploma/livello (§1) e chiedere alla scuola se ha un ufficio relazioni con le aziende.
2. Mandare le candidature spontanee alle **prime 15–20 aziende del CSV** (nel frattempo il radar non serve per questo).
3. Creare gli **avvisi email** su Indeed, Welcome to the Jungle, LinkedIn, JobTeaser per "alternance développeur" (e variante IA).
4. Inviare il messaggio al supporto francetravail.io (§5).
5. Creare `CV_base/` con i 2 CV base (alternanza e stage) e verificare che la cartella delle lettere sul Desktop sia leggibile da Claude Code (`--add-dir`, §10).
6. Avviare Claude Code con **P0 → P6**. Prima di P9 generare `profile/` dai CV e dalle lettere (prompt in §10).
7. Aggiungere Adzuna (stage) e Gmail (lettura avvisi, poi bozze).
