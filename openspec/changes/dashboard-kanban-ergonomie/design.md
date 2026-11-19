# Design

## Context

`web/src/routes/+page.svelte` affiche « Nouvelles », puis une `<section>` par statut de `COLONNES` dans `.tableau` (flex horizontal, colonnes de 17rem), et les écartées dans une grille en dessous quand le filtre est actif. `CarteSuivi.svelte` rend un `<article>` : titre lien vers `/fiche/{genre}/{id}`, puces, lien externe, puis un formulaire `?/statut` avec un `<select>` de `atteignables(statut)` et un bouton « Changer ». La query string des filtres (`suite`) est recopiée dans l'action. Les erreurs remontent par `form.erreur` sur la carte visée. Les tokens, `.badge` et `envoi.ts` viennent de `dashboard-fondations-visuelles`, qui doit être archivé avant ce change.

## Goals / Non-Goals

**Goals:**
- Voir d'un coup d'œil où sont les candidatures, et déplacer une carte en deux gestes.
- Garder le fonctionnement sans JavaScript et au clavier, ainsi que les mêmes règles de transition.

**Non-Goals:**
- Pas de glisser-déposer : un ajout coûteux en accessibilité pour un gain faible sur une poignée de cartes.
- Pas de colonne masquable ni de mémorisation de préférences.

## Decisions

- **Grille de colonnes à défilement aimanté.** `.tableau` passe en `display: grid; grid-auto-flow: column; grid-auto-columns: minmax(16rem, 1fr); overflow-x: auto; scroll-snap-type: x proximity`. Les colonnes vides reçoivent la classe `vide` posée par Svelte (`cartes.length === 0`) et une largeur de 9rem. Un dégradé en bord droit (`mask-image`) indique qu'il reste des colonnes, seulement quand la grille déborde. *Alternative écartée :* passer à la ligne (`flex-wrap`), qui casse la lecture de gauche à droite du parcours de candidature.
- **En-tête collant.** Le `h2` de colonne devient `position: sticky; top: 0` dans la colonne, avec une pastille `--statut-{groupe}` et l'effectif en `.donnee`. Le groupe vient d'une table `GROUPE_STATUT` ajoutée à `web/src/lib/statuts.ts`, à côté de `LIBELLES` (même source, pas de copie).
- **Carte : lien étiré.** Le `<a>` du titre porte un `::after` en `position: absolute; inset: 0`, et l'`<article>` est en `position: relative`. Le lien externe et le menu sont en `position: relative; z-index: 1`, au-dessus du pseudo-élément. Ordre de tabulation : titre, lien externe, menu. *Alternative écartée :* un `<article>` entier dans un `<a>`, interdit puisque la carte contient d'autres éléments interactifs.
- **Menu « Déplacer » = `<details>` + un `<form>` avec un bouton par statut.** `<details class="menu"><summary>Déplacer</summary><form method="POST" action="?/statut{suite}" use:enhance={...}>` avec les champs cachés `genre` et `id` et un `<button name="statut" value={s} aria-label="Passer « {titre} » à {libellé}">` par statut atteignable. L'action serveur ne change pas : elle reçoit toujours `statut` dans le formulaire. *Alternatives écartées :* un `<select>` qui envoie au `change` (un utilisateur clavier envoie sans le vouloir en parcourant les options) ; un menu ARIA `role="menu"` (gestion des flèches à écrire, pour rien). « Écartée » est séparée des autres actions par un trait et rendue avec `.btn-discret`.
- **Retour après action.** L'action `?/statut` renvoie `{ ok: true, genre, id, titre, statut }`. La page affiche `« {titre} » passée à {libellé}.` dans un `role="status"` placé avant le tableau. Le callback `use:enhance` de la carte appelle `envoi` (état en cours), puis, après `update()`, `document.getElementById('carte-{genre}-{id}')?.focus()` sur l'`<article tabindex="-1">`. Le `<details>` se referme de lui-même, puisque la carte est recréée dans sa nouvelle colonne.
- **Filtres sur une ligne.** `.filtres` en `flex-wrap` avec `align-items: end`. Le bouton « Filtrer » prend la classe `.btn-secondaire`, puisque l'action principale de la page est le déplacement et non le filtre.

## Risks / Trade-offs

- [Le pseudo-élément du lien étiré capte la sélection de texte de la carte] → c'est accepté : le texte de la carte est court et se retrouve dans la fiche.
- [Un `<details>` ouvert reste ouvert si l'utilisateur clique ailleurs] → un petit gestionnaire `toggle` ferme les autres menus quand un menu s'ouvre. Sans JavaScript, plusieurs menus peuvent rester ouverts, ce qui est sans gravité.
- [Les noms accessibles longs (« Passer « Développeur web en alternance » à Candidature envoyée »)] → le libellé visible reste court ; seul le nom accessible est long, ce qu'exige l'unicité des noms dans `a11y.spec.ts`.
- [Les tests e2e actuels visent « Passer à »/« Changer »] → ils sont réécrits dans le même lot. Les scénarios couverts (clavier, refus, écartées, filtres) restent les mêmes.
