# Proposal

## Why

Le tableau de bord (C7) fonctionne, mais il n'a pas de système visuel. Sept variables de couleur, des marges en rem codées en dur, la police système, aucun point de rupture, des boutons sans état de survol, d'attente ni d'inactivité. Le badge « sous le seuil » emprunte le rouge d'erreur. Les captures de `web/test-results/` montrent une interface lisible mais sans hiérarchie. Avant de retravailler le kanban, les listes et les statistiques (changes `dashboard-kanban-ergonomie`, `dashboard-listes-et-fiches`, `dashboard-stats-visuelles`), il faut une base commune. Sinon, chaque page invente ses propres valeurs.

## What Changes

- Jeu de tokens dans `web/src/app.css`, pour les thèmes clair et sombre : surfaces, texte, bordures, accent, couleurs sémantiques (succès, avertissement, danger, info) et trois groupes de statut (en cours, positif, clos). S'y ajoutent les échelles d'espacement, de taille de texte, de rayon et d'ombre.
- Typographie : IBM Plex Sans pour l'interface, IBM Plex Mono pour les chiffres alignés (scores, km, dates). Les deux sont auto-hébergées par paquets npm et servies depuis `127.0.0.1`. Chiffres tabulaires dans les données, mesure de 65 caractères pour la prose.
- Boutons primaire, secondaire et discret, avec états survol, actif, désactivé et « en cours » pendant un envoi de formulaire.
- Badges : neutre, score (haut, moyen, bas) et groupe de statut. « Sous le seuil » passe en avertissement.
- Mouvement réduit respecté ; points de rupture 48rem et 64rem ; aucune page ne défile horizontalement à 375px de large, sauf le kanban.
- Contrôle `axe` dans Playwright, zéro violation sur chaque page dans les deux thèmes. Le contrôle de contraste maison reste en place.
- Hors périmètre : refonte des pages elles-mêmes (trois changes suivants), bascule manuelle de thème, framework CSS, bibliothèque de composants, nouvelles données.

## Capabilities

### New Capabilities
- `dashboard-design` : règles visuelles et d'accessibilité communes à toutes les pages du tableau de bord (tokens, typographie, états interactifs, accessibilité vérifiée, mouvement réduit, petit écran).

### Modified Capabilities

## Impact

- `web/src/app.css` réécrit autour des tokens ; retouches de classes dans les `.svelte` existants, sans changement de données ni de route.
- Nouvelles dépendances npm, toutes gratuites et locales : `@fontsource/ibm-plex-sans`, `@fontsource/ibm-plex-mono` (exécution), `@axe-core/playwright` (dev).
- `web/e2e/a11y.spec.ts` : ajout du passage `axe` ; les sélecteurs du contrôle de contraste suivent les classes renommées.
- Aucun changement Python, base, transitions ni texte visible hors libellés de boutons.
