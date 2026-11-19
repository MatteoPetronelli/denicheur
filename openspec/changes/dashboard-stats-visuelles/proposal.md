# Proposal

## Why

La page `/stats` (capture `web/test-results/_stats-light.png`) aligne dix tuiles identiques et un tableau de huit statuts × deux colonnes, presque tous à zéro. Le parcours vues → retenues → notées → envoyées est l'information principale, mais il faut lire quatre tuiles et faire les divisions de tête pour voir où se perdent les offres. Un tableau de zéros prend la moitié de la page. Rien ne distingue le total des réponses de sa ventilation, ni une exécution en erreur d'une exécution saine.

## What Changes

- L'entonnoir des offres en barres horizontales proportionnelles, avec pour chaque étape la valeur, la part des offres vues et le taux de passage depuis l'étape précédente, écrits en texte. Il remplace les quatre tuiles « Offres ».
- La répartition des candidatures par statut en barres groupées (offres et entreprises), à l'échelle du plus grand effectif. Les statuts à zéro restent listés en discret. Elle remplace le tableau.
- Des tuiles hiérarchisées : le total des réponses en grand, la ventilation offres et entreprises en dessous, plus petite. Les tuiles du modèle local sont alignées sur le même gabarit.
- Les dernières exécutions : nombres alignés à droite, mode en badge neutre, erreurs en badge danger quand il y en a, « aucune » en discret.
- La page `/projet` adopte la typographie de lecture des fondations (titres espacés, 65 caractères par ligne), sans changement de texte.
- Hors périmètre : bibliothèque de graphiques, courbes dans le temps, nouvelles mesures, nouvelle requête SQL.

## Capabilities

### New Capabilities

### Modified Capabilities
- `dashboard-stats` : ajout de *Offer funnel* et *Status distribution* ; *Recent runs* change (signalement des exécutions en erreur).

## Impact

- `web/src/routes/stats/+page.svelte`, `web/src/routes/projet/+page.svelte`, `web/src/app.css` ; nouveau `web/src/lib/entonnoir.ts` (étapes, parts et taux, sans division par zéro) avec son test.
- `web/e2e/pages.spec.ts` et `web/e2e/a11y.spec.ts` : sélecteurs des chiffres de la page stats.
- Dépend de `dashboard-fondations-visuelles`. Indépendant des deux autres changes. Aucun changement côté Python, `web/src/lib/server/stats.ts` ni base.
