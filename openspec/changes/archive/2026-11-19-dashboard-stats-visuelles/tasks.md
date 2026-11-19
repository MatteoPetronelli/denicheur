# Tasks

## 1. Lot 1 : entonnoir, répartition, exécutions et page projet (skills : frontend-design, design-system, fixing-accessibility, sveltekit, browser-proof, tdd-workflow, mutation-verified-testing, avoid-ai-writing)

- [x] 1.1 Étape bloquante : vérifier que `dashboard-fondations-visuelles` est archivé (`openspec/specs/dashboard-design/spec.md` existe) et que la gate web est verte. Vérifié : les deux conditions sont remplies.
- [x] 1.2 `web/src/lib/entonnoir.ts` : `etapes(offres)`. Tests Vitest : (40, 12, 12, 8) donne des parts 1 / 0,3 / 0,3 / 0,2 et des taux `null` / 0,3 / 1 / 0,667 ; (0, 0, 0, 0) donne des parts et des taux `null` partout, sans `NaN`. Plus une fonction d'affichage `pourcent(x)` (`null` → « — », 0,667 → « 67 % »), testée. Vérifié : tests verts ; mutation : retirer la garde du dénominateur nul → rouge.
- [x] 1.3 Entonnoir sur `/stats` (`ol.entonnoir`, barres `aria-hidden` à `--part`, valeur et pourcentages en texte), à la place des quatre tuiles « Offres ». Test Playwright sur la base de démonstration : les valeurs attendues par `pages.spec.ts` sont lues dans l'entonnoir, et chaque étape a un texte « % des vues ». Test Vitest de la page avec une base vide : aucune occurrence de `NaN` ni de `Infinity` dans le HTML. Vérifié : tests verts ; mutation : diviser par `vues` sans garde → rouge.
- [x] 1.4 Répartition par statut (`dl.repartition`, deux barres par statut à l'échelle du maximum, lignes à zéro en discret), à la place du tableau ; tuiles de réponses et du modèle local hiérarchisées. Test Playwright : « Intéressante » montre « Entreprises 1 » ; le scénario *Company applications* (Vitest existant) reste vert. Vérifié : tests verts ; mutation : inverser offres et entreprises → rouge.
- [x] 1.5 Exécutions : nombres à droite en `.donnee`, mode en badge, erreurs en `.badge.-danger` ou « aucune » en discret, texte d'erreur toujours absent. Test Playwright : la ligne du 17/11 contient un badge danger « 1 erreur », celle du 18/11 n'en a pas. Le test « texte d'erreur absent » reste vert. Vérifié : tests verts ; mutation : afficher le badge danger quand `nbErreurs` vaut 0 → rouge.
- [x] 1.6 `/projet` en `.prose`, sans changement de texte ; `@media (forced-colors: active)` pour les barres. Vérifié : le test « pas de donnée personnelle » est vert et le texte de la page est identique à avant (`git diff` limité aux classes).
- [x] 1.7 Sélecteurs de `web/e2e/a11y.spec.ts` pour `/stats` mis à jour (entonnoir, répartition, badges), `axe` et le contraste maison verts dans les deux thèmes ; `web-design-guidelines` sur les deux pages ; `avoid-ai-writing` sur les nouveaux libellés ; `browser-proof` à 1280 px et 375 px, comparé à `docs/captures/avant-c8/_stats-light.png`, résultat noté dans `design.md` (`## Résultats du lot 1`). Vérifié : le rapport ne laisse aucune anomalie ouverte.
- [x] 1.8 Gate complète verte (web et Python), `openspec validate dashboard-stats-visuelles --strict`, `graphify update .`.

## Workflow follow-up

- Archiver le change, puis `openspec validate --specs --strict`.
- `npm run captures` pour `docs/captures/statistiques.png`. Une fois les quatre changes archivés, mettre à jour l'état de C8 dans `CLAUDE.md` et la roadmap.
