# Proposal

## Why

`/entreprises` affiche 50 lignes de 11 colonnes, avec deux boutons pleins par ligne : la capture `web/test-results/entreprises.png` montre un mur de boutons bleus où le nom de l'entreprise se perd. Les colonnes vides (Activité, Effectif) restent blanches sans « — ». Les nombres sont alignés à gauche et le statut est en texte brut. Sous 60rem, tout défile de côté. La pagination n'offre que « précédente » et « suivante » pour environ 24 pages. Sur `/offres`, le badge « sous le seuil » est collé au score. Les fiches commencent par « ← Retour au tableau » même quand on vient de `/entreprises`, et leurs détails tiennent dans une colonne étroite.

## What Changes

- Tables : en-tête collant, nombres alignés à droite en chiffres tabulaires, « — » pour une valeur absente, statut en badge de groupe, lignes plus denses. Pour les entreprises, nom, activité et commune sont réunis dans une cellule, et statut et date de contact dans une autre (11 colonnes ramenées à 8).
- Actions par ligne : « Contactée » en bouton secondaire et « Écartée » en bouton discret. Plus de mur de boutons pleins ; les noms accessibles ne changent pas.
- Sous 48rem, chaque ligne devient une carte libellée, en CSS seulement, à partir du même markup.
- Pagination numérotée : première page, dernière page et les pages voisines de la page courante, avec des ellipses.
- Compteur de résultats et filtres sur une ligne, comme sur le tableau.
- Fiches : fil d'Ariane selon la nature (« Entreprises › Beta SA » ou « Offres › Titre »), statut en badge, détails sur deux colonnes dès 48rem, brouillons lisibles (65 caractères par ligne, retours à la ligne gardés, police d'interface).
- Hors périmètre : tri par colonne, changement de statut depuis une fiche, nouvelles colonnes ou nouveaux filtres.

## Capabilities

### New Capabilities

### Modified Capabilities
- `dashboard-tracking` : les requirements *Companies page*, *Offers page* et *Drafts are read-only* changent (présentation des valeurs, petit écran, pagination numérotée, brouillons lisibles). Ajout de *Record page navigation* (fil d'Ariane et statut des fiches).

## Impact

- `web/src/routes/entreprises/+page.svelte`, `web/src/routes/offres/+page.svelte`, `web/src/routes/fiche/[genre]/[id]/+page.svelte`, `web/src/app.css` ; nouveau `web/src/lib/pagination.ts` (pages visibles) avec son test.
- `web/e2e/suivi.spec.ts` et `web/e2e/a11y.spec.ts` : sélecteurs de pagination et de fiche.
- Dépend de `dashboard-fondations-visuelles`. Indépendant de `dashboard-kanban-ergonomie`. Aucun changement côté Python, requêtes SQL ni base.
