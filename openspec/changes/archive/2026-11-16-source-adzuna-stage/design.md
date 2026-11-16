# Design

## Context

C1 et C2 sont archivés. `run` collecte des sources `(config, now) -> list[Offre]`, dédoublonne, géolocalise, préfiltre, note avec Ollama et notifie. Seule la collecte d'alternance existe (`derniere_collecte:alternance`, toutes les 3 h) ; `Deps.sources` porte LBA et l'e-mail. `Secrets` a déjà `adzuna_app_id`, `adzuna_app_key` et `adzuna_enabled`. `PisteStage` a `duree_mois`, `debut`, `frequence_heures` (24). Les contrats viennent de `docs/plans/2026-11-16-denicheur-roadmap.md` §4 C3 et font foi.

Contraintes : 100 % local et gratuit (Adzuna est gratuit), tests hors réseau (`MockTransport`), aucune clé dans les erreurs, journaux ou `executions`, aucun scraping.

## Goals / Non-Goals

**Goals:**
- Alimenter la piste stage avec les offres Adzuna autour de Mareil-Marly, au plus 10 requêtes par jour.
- Réutiliser tel quel le pipeline (dédoublonnage, géo, préfiltre, scoring, digest).

**Non-Goals:**
- Règle de préfiltre sur la durée ou la date de début : les offres Adzuna ont rarement ces champs, le scoring les juge sur le texte.
- Suivi de `redirect_url` ou description complète (Adzuna tronque la description ; assumé).

## Decisions

1. **Clé en paramètres de requête** : Adzuna n'accepte `app_id` et `app_key` que dans l'URL. `get_json` laisse remonter une `HTTPStatusError` dont le message contient l'URL ; la source SHALL attraper `httpx.HTTPStatusError` et lever `ErreurAdzuna("HTTP <code>")`. `run` ne consigne déjà que le nom du type d'exception, la garde protège les journaux et tout futur affichage. Alternative écartée : en-têtes (non supportés par l'API).
2. **Signature** : `collecter(config, http, now, app_id, app_key)`, liée dans `__main__` comme LBA, avec un client HTTP dédié sans l'en-tête LBA.
3. **Dictionnaire séparé** : `Deps.sources_stage` (vide par défaut pour ne pas casser les tests existants), rempli par `__main__` comme la source e-mail. Alternatives écartées : un registre `SOURCES_STAGE` (une seule source, indirection inutile) et un drapeau par source. `Deps.sources` garde l'alternance et l'e-mail.
4. **Échéance stage** : `_stage_due(deps, mode, now)` : mode `stage` vrai ; mode `auto` vrai si dans la plage horaire et `parametres.derniere_collecte:stage` n'est pas la date Paris du jour. Le mode `alternance` ne collecte plus que l'alternance. `_collecter` est factorisé sur une liste de sources et une clé de paramètre ; dédoublonnage, géo et insertion sont communs. Le mode `digest` ne collecte rien (inchangé).
5. **Mots-clés configurables** : `PisteStage.mots_cles_recherche: list[str]` borné à 10, valeur de départ `["développeur", "développeur web", "développeur python", "data", "intelligence artificielle"]` ; chaque requête vaut `"<mot> stage"`. Le dédoublonnage interne à la source se fait par `id` avant le retour.
6. **Piste** : titre d'abord, puis description (règle de la roadmap), avec les mêmes listes de mots que la source e-mail, sans accents. Risque assumé : un « stage » cité dans une description d'alternance ; le préfiltre et le scoring plafonnent le reste.
7. **Durée** : regex `(\d{1,2})\s*mois` sur titre puis description ; sinon `None`.
8. **Télétravail et piste partagés** : le motif de télétravail et la déduction de piste de la source e-mail passent dans `sources/texte.py`, utilisé par les deux sources, pour ne pas dupliquer.
9. **Lien propre** : `redirect_url` porte `?utm_medium=api&utm_source=<App ID>` (constaté sur la capture réelle) ; la source applique `lien_propre` (déjà utilisé par les e-mails) pour qu'aucun identifiant de compte n'entre en base, dans Telegram ou les journaux. La fixture commitée remplace l'App ID par `APPID_MASQUE`.
10. **Date** : `created` (ISO avec `Z`) converti en UTC **avec** fuseau, comme LBA : le préfiltre le compare à `now` (aware) ; le stockage normalise ensuite en UTC naïf.
11. **Lieu de recherche dédié** : Adzuna ne reconnaît pas toutes les communes (« Mareil-Marly » renvoie 0 résultat, même pour « développeur » ; la recherche par coordonnées est refusée en 400). `PisteStage.lieu_recherche` vaut « Marly-le-Roi » (commune voisine reconnue, 53 résultats pour « stage développeur » à 25 km), indépendamment de `centre.commune` ; le filtre de distance du pipeline reste calculé depuis les coordonnées du centre. Le mode d'un 503 isolé est couvert par la politique de retry de `get_json`.
12. **Quota** : au plus 10 requêtes par jour (une collecte par jour, au plus 10 mots-clés) ; les en-têtes de quota éventuels sont notés pendant la capture de la fixture.

## Risks / Trade-offs

- [Beaucoup de résultats hors métier : Adzuna agrège et « stage » est un mot courant] → le préfiltre (`mots_cles_titre`) et le score filtrent ; la proportion se mesure sur la fixture réelle.
- [Descriptions tronquées → score peu discriminant] → neutre faute d'information, comme pour les e-mails.
- [Expiration non fournie] → `expire_le = None`, `max_days_old` borne l'ancienneté.
- [Une clé qui fuite par une exception] → garde de la décision 1, test sur 401 et 429.
- [Le mode `alternance` ne collecte plus que l'alternance] → comportement inchangé pour l'alternance, couvert par un test.

## Migration Plan

Aucune migration de base. Nouveau paramètre `derniere_collecte:stage` créé à la première collecte. Retour arrière : retirer `ADZUNA_APP_KEY` du `.env` désactive la source. Prérequis humains : aucun (les clés sont dans `.env`).
