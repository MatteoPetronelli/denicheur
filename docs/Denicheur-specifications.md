# Dénicheur — Radar de stages et d'alternances

> Assistant personnel de recherche de stage et d'alternance : il collecte les offres via des sources officielles,
> les évalue avec un LLM par rapport au profil de Matteo et envoie chaque jour un digest **en français** sur Telegram.
> Tout ce qui est visible par l'utilisateur (messages Telegram, brouillons, dashboard, logs utilisateur) est **en français**.
> Ce document est rédigé en italien. Les textes de l'application sont en français.

Nom de travail : **Dénicheur** (renommable). Slug du dépôt : `denicheur`.

---

## 1. Objectif

Réduire le temps passé à chercher et augmenter la qualité des candidatures, sans aucun contournement de protections anti-bot.

Deux recherches en parallèle :

| Piste | Détail |
|---|---|
| **Stage** | 5 à 6 mois, début **janvier 2027**, février 2027 au plus tard. Profil : développeur web & IA. |
| **Alternance** | 1 à 2 ans, rythme **1 semaine école / 2 semaines entreprise** (déjà validé avec l'école, qui est déjà en cours). Début : **dès que possible**, y compris immédiat. Piste **prioritaire et urgente**. |

Zone : **rayon de 25 km autour de Mareil-Marly (78750)**.
Niveau : Bac+3 (3e année de Bachelor Informatique).

### Critères de réussite
- Chaque matin, un digest Telegram avec les 5 à 10 meilleures offres nouvelles, classées par score.
- Pour l'alternance : alerte Telegram **immédiate** (collecte toutes les 3 heures en journée) pour les offres au score ≥ 80.
- Aucune offre hors zone (> 25 km) ni hors type de contrat dans le digest.
- Pour chaque offre retenue, un brouillon de candidature en français prêt à relire, en un clic.
- Suivi de toutes les candidatures avec relance proposée à J+7.
- Coût total d'exploitation ≤ 5 €/mois (essentiellement les appels LLM).

---

## 2. Profil candidat (utilisé pour le scoring)

Données **sans informations personnelles** (pas de téléphone, date de naissance ni adresse précise envoyés au LLM).

- **Compétences principales** : React, TypeScript, JavaScript (Node.js), SvelteKit.
- **Niveau intermédiaire** : Python (FastAPI), SQL (PostgreSQL), API REST / LLM.
- **IA** : prompt engineering, systèmes multi-agents, NLP (FinBERT), API Mistral, développement assisté par IA (Claude Code, Antigravity).
- **Notions** : Rust (Tauri), C# (.NET Blazor), Java, Go.
- **Expérience** : stage développeur web (juin–juillet 2026) : application de gestion de garanties (C# Blazor, FastAPI, PostgreSQL, Alembic, GitHub Actions, SonarCloud).
- **Projets** : web app JO Paris 2024 (SvelteKit, Vercel), assistant boursier IA multi-agents, bot Discord LLM, RiftMind (Rust/Tauri, 129 tests).
- **Langues** : italien et français bilingues, anglais B2.
- **Soft skills** : autonomie, rigueur, esprit d'équipe.

Le fichier `profile/profil.md` contient cette version sans données personnelles. Le CV complet n'est jamais envoyé au LLM.

---

## 3. Périmètre géographique

- Centre : Mareil-Marly (78750), coordonnées à obtenir via l'API Adresse (`api-adresse.data.gouv.fr`) ou `geo.api.gouv.fr`, puis mises en configuration.
- Rayon : **25 km** (paramètre `rayon_km`).
- Distance calculée par formule de Haversine entre le centre et le lieu de l'offre (coordonnées de l'API, sinon géocodage de la commune).
- La distance est affichée dans chaque message (« 4 km »). Si le lieu est inconnu : offre marquée « lieu à vérifier », jamais éliminée automatiquement.
- Télétravail complet : exclu par défaut (`inclure_teletravail_complet: false`). Hybride accepté si le site est dans le rayon.

---

## 4. Sources de données (légales et sans CAPTCHA)

| Source | Usage | Remarque |
|---|---|---|
| **API Offres d'emploi (France Travail)** | Offres actives, filtres par mots-clés, commune/distance, type de contrat | Compte gratuit sur francetravail.io, authentification OAuth. Ne couvre que les offres déposées sur France Travail. |
| **API Adzuna** (France) | Agrégateur multi-sources | App ID / App Key gratuits. Attention à la limite de requêtes. |
| **API La bonne alternance** (`api.apprentissage.beta.gouv.fr`, route `GET /job/v1/search`) | **Source principale de l'alternance** : offres (La bonne alternance, France Travail, partenaires) et entreprises à fort potentiel (`recruteurs_lba`) pour les candidatures spontanées | Accès libre : clé d'API gratuite créée sur le site (clé production, lecture seule). 60 appels/min, 150 résultats max par source. Filtres : coordonnées + rayon, codes ROME (M1805, M1806, M1807), niveau de diplôme. Le champ `contract.start_type = des_que_possible` signale un recrutement urgent. Usage non lucratif uniquement. |
| **La Bonne Boîte** | Entreprises à fort potentiel d'embauche pour une candidature spontanée | Accès conditionné : le jeton est délivré mais la recherche renvoie 403 « Invalid scope » sans habilitation. Demande à faire au support francetravail.io. Non bloquant : `recruteurs_lba` et Recherche d'entreprises couvrent le besoin. |
| **API Recherche d'entreprises** | Liste des entreprises par code NAF, code postal et effectif | Gratuite, sans clé. Sert à la phase « candidatures spontanées ». |
| **Alertes e-mail** (Indeed, LinkedIn, Welcome to the Jungle) | Phase 2 : lecture de la boîte Gmail via IMAP ou API Gmail | Aucun scraping : on lit seulement les alertes que l'utilisateur reçoit déjà. |

### Interdits
- Aucun scraping de pages protégées, aucun contournement de CAPTCHA ou de vérification anti-bot.
- Aucune candidature envoyée automatiquement : **l'envoi final est toujours manuel**.
- Respect des limites de requêtes (retry avec backoff, cache des réponses).

---

## 5. Architecture

```
GitHub Actions (cron)                    Vercel
┌──────────────────────┐                 ┌──────────────────────────┐
│ collect → normalize  │                 │ /api/telegram (webhook)  │
│ → dedupe → geofilter │ ──► Postgres ◄──│ boutons, commandes       │
│ → prefilter → score  │     (Neon)      │ dashboard (SvelteKit)    │
│ → notify (Telegram)  │                 └──────────────────────────┘
└──────────────────────┘
```

Pourquoi Postgres et non SQLite : le job (GitHub Actions) et le webhook Telegram (Vercel) doivent partager la même base.

### Pipeline (quotidien pour le stage, toutes les 3 heures en journée pour l'alternance)
1. **Collecte** : requêtes pour les deux pistes (stage, alternance) × mots-clés (voir `config/recherches.yaml`).
2. **Normalisation** : schéma unique `Offre` (titre, entreprise, lieu, lat/lon, type de contrat, durée, description, URL, source, date de publication).
3. **Déduplication** : hash sur (entreprise normalisée, titre normalisé, commune) + URL.
4. **Filtre géographique** : élimination au-delà de 25 km.
5. **Préfiltre par règles** (sans LLM) :
   - mots éliminatoires : « senior », « confirmé », « 3 ans d'expérience », etc. ;
   - contrat ni stage ni alternance : éliminé ;
   - offre expirée ou publiée il y a plus de 30 jours : éliminée.
6. **Scoring LLM** sur les offres restantes (voir §6).
7. **Stockage** et **notification** Telegram des offres dont le score ≥ seuil.

---

## 6. Scoring LLM

Modèle : **Claude Sonnet 5.5** (`claude-sonnet-5-5`) avec `output_config.effort = "low"` pour le scoring (classification à sortie JSON, fort volume). Sortie **JSON validée par pydantic**, réponse en français. L'effort ne change pas entre deux requêtes du même type (cela invalide le cache) ; avant de figer `low`, comparer avec `medium` sur ~20 offres étiquetées à la main.

### Barème (100 points)
| Critère | Points |
|---|---|
| Adéquation des compétences (React/TS/Python/IA/SQL) | 40 |
| Type, durée et calendrier (voir ci-dessous) | 20 |
| Localisation / distance | 15 |
| Niveau demandé vs Bac+3 | 15 |
| Intérêt du poste (IA, produit, autonomie, apprentissage) | 10 |

### Règles par piste
- **Stage** : durée 5–6 mois, début janvier–février 2027. Durée ou date absentes : neutre. Durée hors 5–6 mois : malus + mention dans le message.
- **Alternance** : durée 1–2 ans. Démarrage immédiat ou très proche : **bonus** (le candidat est déjà inscrit à l'école, seul le contrat en entreprise manque). Début dans plus de 6 mois : malus. Rythme annoncé ≠ 1 semaine école / 2 semaines entreprise : **alerte, pas élimination** (le rythme 1/2 est déjà validé avec l'école, mais certaines entreprises annoncent un autre rythme à discuter).

### Sortie attendue
```json
{
  "score": 0,
  "type": "stage | alternance | autre",
  "points_forts": ["..."],
  "points_faibles": ["..."],
  "alerte": null,
  "projet_a_citer": "RiftMind | Assistant boursier IA | Web app JO 2024 | Bot Discord | ...",
  "resume": "2 phrases en français"
}
```

Seuil de notification par défaut : 65/100 (`score_min`). Les offres sous le seuil restent consultables dans le dashboard.

### Contrôle des coûts
- Plafond d'appels LLM par jour (`llm_max_appels_jour`, par défaut 150).
- Préfiltre par règles avant le LLM, cache par offre (jamais deux fois la même offre).
- Prompt système et profil mis en cache.

---

## 7. Bot Telegram (en français)

Un seul utilisateur autorisé : toute requête dont `chat_id` ≠ `TELEGRAM_CHAT_ID` est ignorée.

### Digest quotidien
Envoyé à **08h30 (Europe/Paris)**. GitHub Actions travaille en UTC : le code vérifie l'heure locale (deux crons, heure d'hiver et d'été) pour éviter le décalage.

Exemple de message :

```
🎯 Stage · Développeur Full Stack IA
🏢 Exemple SAS · 📍 Saint-Germain-en-Laye (4 km)
🕒 6 mois · début février 2027
⭐ Score 86/100

✅ React/TypeScript, Python, projets IA
⚠️ Demande des notions Docker

💡 Projet à citer : Assistant boursier IA
🔗 Voir l'offre
```

Boutons : `✅ Je postule` · `✉️ Brouillon` · `🔔 Rappel J+7` · `❌ Ignorer`

### Alertes immédiates (alternance)
Entre deux digests, toute nouvelle offre d'**alternance** au score ≥ 80 est envoyée tout de suite (préfixe « 🚨 Alternance »), avec les mêmes boutons. Plage horaire : 08h00–20h00, Europe/Paris.

### Commandes
| Commande | Action |
|---|---|
| `/aujourdhui` | Digest du jour à la demande |
| `/stage` / `/alternance` | Meilleures offres par piste |
| `/candidatures` | Liste et statut des candidatures |
| `/relances` | Candidatures à relancer |
| `/stats` | Offres vues, candidatures envoyées, réponses |
| `/pause` / `/reprendre` | Suspend ou reprend les notifications |
| `/config` | Affiche les paramètres actifs (rayon, seuil, mots-clés) |

### Technique
- Webhook (`setWebhook`) vers une fonction Vercel, avec `secret_token` vérifié à chaque requête.
- Alerte Telegram si le job quotidien échoue (« ⚠️ La collecte du jour a échoué »).

---

## 8. Brouillons de candidature (en français)

Déclenchés par le bouton « Brouillon ». Produisent un e-mail court (≈ 120–180 mots) et, au besoin, une version plus longue de lettre de motivation.

Règles :
- Basé uniquement sur le profil et l'offre : **aucune information inventée**.
- Cite **un projet concret** adapté à l'offre et un détail propre à l'entreprise.
- Mentionne la disponibilité (stage : janvier/février 2027, 5–6 mois ; alternance : rythme 1 semaine école / 2 semaines entreprise).
- Ton professionnel, direct, sans formules creuses. Vouvoiement.
- Le brouillon est envoyé dans Telegram pour relecture. L'envoi se fait manuellement depuis la boîte mail de l'utilisateur.

---

## 9. Suivi des candidatures et relances

Statuts : `nouvelle` → `intéressante` → `candidature_envoyée` → `relancée` → `entretien` → `refus` / `offre` / `sans_réponse`.

- Rappel automatique à **J+7** après l'envoi : brouillon de relance proposé.
- **Une seule relance** par candidature.
- Dashboard (phase 3) : kanban par statut, filtres stage/alternance, historique.

---

## 10. Candidatures spontanées (phase 2)

1. Liste d'entreprises : API Recherche d'entreprises (codes NAF informatique, ex. 62.01Z, communes du rayon, effectif PME) + La Bonne Boîte.
2. Pour chaque entreprise : recherche manuelle assistée (site, stack, blog technique, organisation GitHub).
3. Brouillon personnalisé avec un élément concret.
4. Plafond : **10 à 15 candidatures par jour**, un seul message par entreprise, envoi manuel.

---

## 11. Données (Postgres)

| Table | Champs principaux |
|---|---|
| `offres` | id, source, source_id, titre, entreprise, commune, lat, lon, distance_km, contrat, duree_mois, debut, description, url, publiee_le, vue_le |
| `scores` | offre_id, piste, score, points_forts, points_faibles, alerte, projet_a_citer, modele, cree_le |
| `candidatures` | id, offre_id, statut, envoyee_le, relance_le, notes |
| `brouillons` | candidature_id, type, contenu, cree_le |
| `executions` | id, debut, fin, offres_collectees, offres_scorees, erreurs, cout_estime |
| `parametres` | clé, valeur (pause, seuil, etc.) |

---

## 12. Stack et structure du dépôt

| Élément | Choix |
|---|---|
| Langage | Python 3.12 (httpx, pydantic, SQLAlchemy, Alembic) |
| Tests | pytest (tests unitaires sur normalisation, dédup, distance, préfiltre, parsing JSON LLM) |
| Qualité | ruff, mypy, pre-commit |
| Exécution | GitHub Actions (cron) |
| Base | Postgres (tier gratuit Neon ou Supabase) |
| Webhook et dashboard | SvelteKit ou Next.js sur Vercel |
| LLM | **Claude Sonnet 5.5** (`claude-sonnet-5-5`) pour tout : effort `low` pour le scoring, `medium` pour les brouillons, lettres et variantes de CV (paramètre `output_config.effort`) |

```
denicheur/
├── .github/workflows/collecte.yml
├── config/
│   ├── recherches.yaml      # mots-clés, pistes, rayon, seuil
│   └── config.example.yaml
├── CV_base/                 # les 2 CV d'origine (alternance, stage) — local, hors git
├── profile/
│   ├── profil.md            # profil sans données personnelles
│   ├── cv_alternance.md     # variante dérivée de CV_base — local, hors git
│   ├── cv_stage.md          # variante dérivée de CV_base — local, hors git
│   ├── lettre_modele.md     # modèle de lettre (style tiré des lettres d'exemple)
│   └── regles_ecriture.md   # ton, longueur, vouvoiement, règles anti-invention
├── src/denicheur/
│   ├── sources/             # france_travail.py, adzuna.py, la_bonne_alternance.py, ...
│   ├── pipeline/            # normalize, dedupe, geo, prefilter
│   ├── scoring/             # prompts, schémas, client LLM
│   ├── telegram/            # envoi, formatage des messages
│   └── db/                  # modèles, migrations
├── web/                     # webhook Telegram + dashboard
├── scripts/test_france_travail.py   # test de couverture de l'API (stage / apprentissage)
├── tests/
└── README.md
```

### Mots-clés de départ (`recherches.yaml`)
- **Stage** : développeur full stack, développeur React, développeur TypeScript, développeur Python, IA générative, LLM, prompt engineering, agents IA, développeur web, automatisation IA.
- **Alternance** : mêmes mots-clés + « alternance », « apprentissage ».
- **Exclusions** : senior, confirmé, expérimenté, manager.
- Filtre sur Claude Code, Cursor, Copilot : bonus de score (développement assisté par IA).

---

## 13. Sécurité, vie privée, contraintes

- Dépôt **privé**. Secrets uniquement dans GitHub Secrets et variables Vercel :
  `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_WEBHOOK_SECRET`, `FRANCE_TRAVAIL_CLIENT_ID`, `FRANCE_TRAVAIL_CLIENT_SECRET`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `LLM_API_KEY`, `DATABASE_URL`.
- Aucune donnée personnelle (téléphone, date de naissance, adresse exacte) dans les prompts ni dans les logs.
- Idempotence : relancer le job ne doit jamais renvoyer deux fois la même offre.
- Robustesse : retry avec backoff, respect des quotas, timeouts, journalisation de chaque exécution dans `executions`.
- Respect des conditions d'utilisation de chaque API.

---

## 14. Points à vérifier avant le développement

1. **Couverture stage et apprentissage** : lancer `scripts/test_france_travail.py` pour mesurer combien d'offres de **stage** et de **contrat d'apprentissage** l'API renvoie réellement dans les 25 km. Si les stages sont quasi absents, s'appuyer davantage sur Adzuna et sur les alertes e-mail ; pour l'alternance, ajouter La Bonne Alternance.
2. **Codes de contrat** : récupérer les référentiels de l'API (type et nature de contrat) pour filtrer alternance / apprentissage / professionnalisation.
3. **Accès API** : La bonne alternance = clé gratuite à créer sur le site (à tester avec le script, test 4). La Bonne Boîte = habilitation à demander au support. « Offres d'emploi v2 » = introuvable dans le catalogue francetravail.io de l'utilisateur (scope refusé) : à demander au support, non bloquant pour l'alternance.
4. **Paramètre de distance** : vérifier si l'API accepte commune + distance, sinon filtrer par Haversine après collecte.
5. **Alternance** : rythme 1 semaine école / 2 semaines entreprise **validé**, début immédiat. Reste à préciser : diplôme visé (niveau demandé par l'école) pour affiner le filtre « niveau ».
6. **Quotas** d'Adzuna et de France Travail, et fréquence de collecte adaptée (une fois par jour suffit au départ).

---

## 15. Feuille de route

| Phase | Contenu | Terminé quand |
|---|---|---|
| **0. Préparation** | Comptes API, bot Telegram, base Postgres, dépôt privé, test de couverture de l'API France Travail | Les clés sont en secrets, un message de test arrive sur Telegram et le résultat du test de couverture est noté |
| **1. MVP** | France Travail + Adzuna → dédup → filtre 25 km → préfiltre → scoring LLM → digest Telegram quotidien | Un digest en français arrive chaque matin, tests passants |
| **2. Interaction** | Webhook Vercel, boutons, brouillons, suivi des candidatures, relances J+7 | Un clic sur « Brouillon » renvoie un brouillon pertinent en moins de 30 s |
| **3. Dashboard** | Kanban, filtres, statistiques, page publique de présentation du projet pour le portfolio | Toutes les candidatures sont consultables et modifiables |
| **4. Spontanées** | Recherche d'entreprises + La Bonne Boîte + brouillons personnalisés | Liste quotidienne de 10 entreprises ciblées avec brouillon |
| **5. Alertes e-mail** | Lecture des alertes Indeed / LinkedIn / WTTJ | Les offres des alertes apparaissent dans le digest sans doublons |

---

## 16. Consignes pour le développement avec Claude Code

- Commencer par la phase 0 et la phase 1 uniquement. Ne pas construire le dashboard avant que le digest fonctionne.
- Écrire les tests en même temps que le code (normalisation, dédup, distance, prompts/parsing).
- Chaque source est un module indépendant avec la même interface (`collecter(config) -> list[Offre]`).
- Les textes en français sont centralisés dans un seul fichier (`messages_fr.py`) pour faciliter les corrections.
- Ne jamais ajouter de contournement de CAPTCHA ni de scraping de pages protégées.
- README du dépôt en français, avec captures d'écran du bot et du dashboard : ce projet sert aussi de **projet de portfolio** (API publiques, LLM, Telegram, CI/CD).
