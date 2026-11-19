# Design

## Context

`web/src/routes/entreprises/+page.svelte` rend un `<table>` de 11 colonnes dans `.defile` (`overflow-x: auto`, `min-width: 60rem`). Chaque ligne a un formulaire `?/statut` avec deux `<button name="statut">` (« Contactée », « Écartée »), dont les `aria-label` uniques sont vérifiés par `a11y.spec.ts`. La pagination se limite à deux liens `rel="prev"` et `rel="next"`, construits par `lien(page)`. `offres/+page.svelte` suit le même schéma avec 6 colonnes. La fiche `fiche/[genre]/[id]/+page.svelte` commence par `← Retour au tableau`, puis un `<dl class="details">` et des `<article class="brouillon">` avec `<pre>`. Les tokens, `.badge`, `.btn-*` et `envoi.ts` viennent de `dashboard-fondations-visuelles`, à archiver avant.

## Goals / Non-Goals

**Goals:**
- Parcourir 1 200 entreprises et repérer celles à contacter sans être gêné par les boutons.
- Les mêmes pages, utilisables sur un téléphone posé à côté de l'ordinateur.

**Non-Goals:**
- Pas de tri par colonne ni de nouveaux filtres : l'ordre priorité puis distance est voulu (spec *Companies page*).
- Pas de changement des requêtes SQL ni des données renvoyées par `load`, sauf ce que demande l'affichage.

## Decisions

- **Moins de colonnes, plus d'information par cellule.** Entreprises : *Entreprise* (nom en lien, puis `activité · commune` en `--discret`, puis lien de candidature), *Distance*, *Priorité*, *Effectif*, *Suivi* (badge de statut et date de contact en dessous), *Brouillons*, *Offre ouverte*, *Actions*. Offres : *Offre* (titre, puis entreprise), *Piste*, *Score* (nombre et badge séparé), *Distance*, *Suivi*. *Alternative écartée :* masquer des colonnes sur écran moyen, ce qui cache de l'information sans le dire.
- **Valeurs.** Une fonction `ouTiret(v)` dans `web/src/lib/format.ts` affiche « — » pour `null`, `undefined` et `''`, avec `aria-label="non renseigné"` sur le `<td>` vide (un tiret lu tel quel n'a pas de sens). Nombres en `.donnee` et `text-align: end`, en-têtes alignés comme leur colonne.
- **En-tête collant.** `thead th { position: sticky; top: 0 }` sur `--surface`. `.defile` reste le conteneur de défilement entre 48rem et 64rem.
- **Cartes sous 48rem, en CSS seul.** `@media (max-width: 48rem)` : `table, tbody, tr, th, td { display: block }`, `thead` masqué visuellement mais gardé pour les lecteurs d'écran, `td::before { content: attr(data-libelle) }` en `--t-xs` `--discret`. Chaque `<td>` reçoit `data-libelle` depuis le même tableau de colonnes qui produit le `<thead>`, déclaré une seule fois dans le script de la page. *Alternative écartée :* un second rendu en `<ul>`, qui doublerait le markup et les tests. *Risque connu :* `display: block` retire la sémantique de tableau dans certains navigateurs ; sous 48rem, c'est acceptable, car chaque valeur porte son libellé.
- **Actions moins bruyantes.** « Contactée » en `.btn-secondaire` et « Écartée » en `.btn-discret`, empilés sous 48rem. L'action primaire d'une liste est d'ouvrir la fiche, pas de marquer. Les `aria-label` restent identiques, donc les tests d'unicité ne changent pas.
- **Pagination numérotée.** Une fonction pure `pagesVisibles(page, total): (number | '…')[]` dans `web/src/lib/pagination.ts` donne 1, la page courante ± 1 et la dernière, avec `'…'` pour chaque trou. Elle sert à `/entreprises` et `/offres` à travers `lien(page)`, qui existe déjà. La page courante porte `aria-current="page"` et n'est pas un lien. `rel="prev"` et `rel="next"` restent sur « Précédente » et « Suivante ».
- **Fil d'Ariane des fiches.** `<nav aria-label="Fil d'Ariane"><ol>` : `Entreprises` ou `Offres` (selon `genre`), puis le titre avec `aria-current="page"`. *Alternative écartée :* `history.back()`, qui dépend de JavaScript et de l'origine de la visite.
- **Fiche.** `dl.details` en `grid-template-columns: max-content 1fr` dès 48rem. Le statut en badge de groupe. Dans les brouillons, `<pre>` passe en police d'interface, `white-space: pre-wrap`, `overflow-wrap: anywhere` et `max-width: 65ch`. On garde l'échappement de Svelte (test XSS existant).

## Risks / Trade-offs

- [Réunir nom, activité et commune change ce que lit un lecteur d'écran par cellule] → le nom reste le `<th scope="row">` de la ligne, et le reste vient après lui dans la même cellule.
- [`data-libelle` désynchronisé du `<thead>`] → les deux sont produits par la même liste de colonnes ; un test Playwright à 375 px vérifie le libellé de chaque valeur.
- [Les tests de pagination visent « Page suivante → »] → le libellé devient « Suivante » avec `rel="next"`, et les tests visent le rôle et `rel`.
