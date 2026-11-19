# Design

## Context

`web/src/routes/stats/+page.svelte` lit `data.stats` (type `Stats` de `web/src/lib/server/stats.ts`) : `offres.{vues, retenues, notees, notifiees}`, `candidatures.offres[statut]` et `candidatures.entreprises[statut]`, `reponses.{total, offres, entreprises}`, `llm.{executions, moyenne_s, total_s}` et `dernieres` (`Execution[]`, avec `nbErreurs`). Elle rend des `ul.cartes` de tuiles et deux tableaux. `/projet` est statique. Les tokens, `.badge`, `.donnee` et `.prose` viennent de `dashboard-fondations-visuelles`, à archiver avant. Un test de `web/e2e/pages.spec.ts` vérifie les chiffres de la page sur la base de démonstration.

## Goals / Non-Goals

**Goals:**
- Voir en une ligne où se perdent les offres, et en une autre où en sont les candidatures.
- Des visuels qui restent justes et lisibles sans CSS, au lecteur d'écran et à zéro.

**Non-Goals:**
- Pas de bibliothèque de graphiques ni de SVG calculé : des barres CSS suffisent pour cinq valeurs.
- Pas de courbe dans le temps : 10 exécutions ne font pas une tendance.

## Decisions

- **Calcul isolé et testé.** `web/src/lib/entonnoir.ts` exporte `etapes(offres): { cle, libelle, valeur, part, taux }[]`. `part = valeur / vues` et `taux = valeur / précédente`, valent `null` quand le dénominateur est 0, et sont arrondis à l'entier en pourcentage à l'affichage seulement. La page ne fait aucune division elle-même. *Alternative écartée :* calculer dans `stats.ts` côté serveur, ce qui mélange la présentation et la requête, déjà testée telle quelle.
- **Barres en CSS, valeur en texte.** Chaque étape est un `<li>` d'un `<ol class="entonnoir">` : libellé, puis valeur en `.donnee`, puis « 30 % des vues · 30 % de l'étape précédente » en `--discret`. La barre est un `<span class="barre" aria-hidden="true" style="--part: 0.3">`, avec `inline-size: calc(var(--part) * 100%)`. La variable inline n'est pas une couleur, donc la garde des couleurs littérales n'est pas concernée. Une `part` nulle donne `--part: 0`. *Alternatives écartées :* `<progress>` et `<meter>`, mal rendus et mal annoncés pour un entonnoir ; SVG, plus de code pour le même résultat.
- **Répartition par statut.** Une `<dl class="repartition">` dans l'ordre de `LIBELLES` : pour chaque statut, le libellé, puis deux lignes « Offres n » et « Entreprises n », chacune avec sa barre à l'échelle du plus grand effectif de la page (`max(1, …)` pour éviter la division par zéro). Une ligne à 0 est en `--discret`. Couleurs : `--accent` pour les offres et `--statut-en-cours` pour les entreprises, avec le libellé écrit à chaque fois, puisque la couleur ne porte jamais seule l'information.
- **Tuiles hiérarchisées.** `.cartes` garde son nom (sélecteurs de test). Une tuile principale (`.nombre` en `--t-2xl`) et une ventilation en `--t-l` dans la même tuile, plutôt que trois tuiles de même poids. Le modèle local garde trois tuiles, au même gabarit.
- **Exécutions.** `.donnee` et `text-align: end` sur les colonnes numériques. Mode en `.badge`. Erreurs : `.badge.-danger` « n erreur(s) » avec un `title` « détail dans les journaux », ou « aucune » en `--discret`. Le texte des erreurs n'est toujours pas lu.
- **Projet.** `main` de `/projet` reçoit `.prose` (65ch, espacement des `h2` en `--e-6`). Aucun texte ne change, pour que le test « pas de donnée personnelle » reste valable tel quel.

## Risks / Trade-offs

- [Des arrondis qui ne tombent pas juste (33 % + 67 %)] → chaque pourcentage est indépendant et ne se somme pas. On l'accepte, et le test vérifie les valeurs du scénario de la spec.
- [Le test de chiffres de `pages.spec.ts` vise les tuiles « offres vues »] → il vise désormais l'entonnoir par son libellé. Les valeurs attendues ne changent pas.
- [Barres peu visibles en mode contraste élevé (`forced-colors`)] → `@media (forced-colors: active)` donne aux barres `background: CanvasText`, et les valeurs restent en texte de toute façon.
