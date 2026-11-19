# Tasks

## 1. Lot 1 : tables, petit écran, pagination et fiches (skills : frontend-design, design-system, fixing-accessibility, sveltekit, browser-proof, tdd-workflow, mutation-verified-testing)

- [ ] 1.1 Étape bloquante : vérifier que `dashboard-fondations-visuelles` est archivé (`openspec/specs/dashboard-design/spec.md` existe) et que la gate web est verte. Vérifié : les deux conditions sont remplies.
- [ ] 1.2 `web/src/lib/pagination.ts` : `pagesVisibles(page, total)`. Tests Vitest : (1, 1) → `[1]` ; (10, 24) → `[1, '…', 9, 10, 11, '…', 24]` ; (2, 24) → `[1, 2, 3, '…', 24]` ; (24, 24) → `[1, '…', 23, 24]` ; page hors bornes ramenée dans les bornes. Vérifié : tests verts ; mutation : supprimer l'ellipse de gauche → rouge.
- [ ] 1.3 `web/src/lib/format.ts` : `ouTiret`, avec tests Vitest (`null`, `undefined`, `''` → « — » ; `0` → « 0 »). Vérifié : tests verts ; mutation : traiter `0` comme vide → rouge.
- [ ] 1.4 `/entreprises` : 8 colonnes (décision du design), « — » pour les valeurs absentes, nombres à droite en `.donnee`, statut en badge et date de contact en dessous, en-tête collant, « Contactée » en `.btn-secondaire` et « Écartée » en `.btn-discret`, pagination numérotée (`aria-current`, `rel`). Tests Playwright : Société 01 affiche « — » pour l'activité ; en page 1 sur 2, la navigation montre « 1 » courant et « 2 » ; les tests « Contactée » et « Écartée » existants restent verts. Vérifié : tests verts ; mutation : afficher `''` au lieu de « — » → rouge.
- [ ] 1.5 `/offres` : 5 colonnes, score à droite et badge « sous le seuil » séparé (avertissement), même pagination. Tests Playwright existants (seuil, piste) verts, plus un test qui vérifie que « sous le seuil » est un élément distinct du nombre. Vérifié : tests verts.
- [ ] 1.6 Petit écran : bloc `@media (max-width: 48rem)` en cartes, `data-libelle` issu de la liste de colonnes de chaque page, `thead` masqué visuellement. Test Playwright à 375 × 812 sur `/entreprises` et `/offres` : `scrollWidth <= innerWidth`, et pour la première ligne, chaque `td` non vide a un `data-libelle` égal à un en-tête du `<thead>`. Vérifié : tests verts ; mutation : retirer `data-libelle` d'une colonne → rouge.
- [ ] 1.7 Fiches : fil d'Ariane (`nav` « Fil d'Ariane », lien vers `/entreprises` ou `/offres`, page courante en `aria-current`), statut en badge, `dl` sur deux colonnes dès 48rem, brouillons en `pre-wrap`, `overflow-wrap: anywhere` et 65ch. Graine e2e : ajouter un brouillon avec une ligne de 300 caractères. Tests Playwright : le fil d'Ariane de Beta SA mène à `/entreprises` ; à 375 px, aucun défilement horizontal sur la fiche ; le test XSS existant reste vert. Vérifié : tests verts ; mutation : retirer `overflow-wrap` → rouge.
- [ ] 1.8 Sélecteurs de `web/e2e/a11y.spec.ts` mis à jour (pagination, fil d'Ariane, badges), `axe` et le contraste maison verts dans les deux thèmes ; `web-design-guidelines` sur les trois pages ; `browser-proof` à 1280 px et 375 px, comparé à `docs/captures/avant-c8/`, résultat noté dans `design.md` (`## Résultats du lot 1`). Vérifié : le rapport ne laisse aucune anomalie ouverte.
- [ ] 1.9 Gate complète verte (web et Python), `openspec validate dashboard-listes-et-fiches --strict`, `graphify update .`.

## Workflow follow-up

- Archiver le change, puis `openspec validate --specs --strict`. Si `dashboard-kanban-ergonomie` a été archivé avant, vérifier que les deux deltas de `dashboard-tracking` ont bien été fusionnés.
- `npm run captures` pour `docs/captures/entreprises.png`, `offres.png` et `fiche.png`.
