# Design

## Context

`web/src/app.css` (374 lignes) porte tout le style. Les sept variables de couleur sont `--fond`, `--surface`, `--texte`, `--discret`, `--bordure`, `--accent` et `--erreur`, avec une surcharge sombre par `prefers-color-scheme`. Il n'y a ni échelle ni point de rupture. Les `.svelte` n'ont pas de bloc `<style>` ni de couleur littérale, et c'est à garder. Le seul composant est `web/src/lib/components/CarteSuivi.svelte`. Formulaires `use:enhance`, utilisables sans JavaScript. `web/e2e/a11y.spec.ts` mesure le contraste sur des sélecteurs nommés (`.puces li`, `.etiquette`, `.cartes .nombre`…) et vérifie l'unicité des noms de boutons. Contraintes projet : 100 % local et gratuit, interface en français.

## Goals / Non-Goals

**Goals:**
- Un seul endroit pour chaque valeur visuelle, consommé par les trois changes suivants.
- Une identité sobre et propre au sujet (carnet de prospection, données denses), pas un gabarit générique.
- Accessibilité prouvée automatiquement, pas seulement relue.

**Non-Goals:**
- Pas de refonte de mise en page des pages (kanban, tables, stats : changes suivants).
- Pas de bascule manuelle de thème : le thème suit le système, comme aujourd'hui.
- Pas de composants Svelte génériques (`Button.svelte`…) : des classes CSS suffisent pour des `<button>` natifs.

## Decisions

- **Tokens en variables CSS, noms français cohérents avec l'existant.** Trois niveaux :
  - primitives non exportées dans le reste du code ;
  - rôles : `--fond`, `--surface`, `--surface-relevee`, `--texte`, `--texte-2`, `--discret`, `--bordure`, `--bordure-forte`, `--accent`, `--accent-texte`, `--succes`, `--avertissement`, `--danger`, `--info`, et pour chacun une variante `-fond` pour les badges ;
  - groupes de statut : `--statut-en-cours` (intéressante, envoyée, relancée), `--statut-positif` (entretien, offre reçue) et `--statut-clos` (refus, sans réponse, écartée).

  *Alternative écartée :* une couleur par statut (8 teintes), illisible et impossible à tenir en contraste dans les deux thèmes.
- **Palette.** On garde les neutres chauds actuels (papier `#f7f7f5`, encre `#1c1c1a`), qui donnent déjà un ton de carnet. Le bleu `#1d4ed8` est la valeur par défaut de mille interfaces : il est remplacé par un **bleu pétrole** (point de départ `#155e75` en clair, `#67c6dd` en sombre). Valeurs sémantiques de départ : succès `#2f6f3e`, avertissement `#8a5300`, danger `#b42318` (gardé). Les valeurs finales sont choisies avec `ui-ux-pro-max` et `frontend-design`, puis validées par `axe` et le contrôle de contraste (≥ 4,5:1 pour le texte, ≥ 3:1 pour les bordures de composants) dans les deux thèmes.
- **Échelles.**
  - Espacement sur une base 4 px : `--e-1` 0.25rem, `--e-2` 0.5rem, `--e-3` 0.75rem, `--e-4` 1rem, `--e-5` 1.5rem, `--e-6` 2rem, `--e-7` 3rem, `--e-8` 4rem.
  - Texte, rapport ≈ 1,25 : `--t-xs` 0.8125rem, `--t-s` 0.875rem, `--t-m` 1rem, `--t-l` 1.25rem, `--t-xl` 1.5625rem, `--t-2xl` 2rem.
  - Rayons : `--r-1` 0.25rem, `--r-2` 0.5rem, `--r-plein` 999px.
  - Deux ombres : `--ombre-1` pour les cartes, `--ombre-2` pour les menus.
  - Points de rupture 48rem et 64rem, écrits en dur dans les `@media` (les variables CSS n'y sont pas permises).
- **IBM Plex Sans + IBM Plex Mono via `@fontsource`.** C'est le choix de l'utilisateur. Plex a de bons accents français, des chiffres tabulaires et une graisse 500 utile pour les libellés. On importe seulement les fichiers `latin` 400, 500 et 600 (Sans) et 400 (Mono) dans `+layout.svelte`. Vite les copie dans `_app/immutable`, donc l'application les sert elle-même, sans CDN. `font-display: swap` (défaut de fontsource) et une pile de repli `system-ui`. Mono seulement pour les valeurs comparées en colonne (`.donnee`), jamais en décoration. *Alternative écartée :* Google Fonts, qui ferait une requête externe et contredirait la règle « rien ne sort de la machine ».
- **Hiérarchie.** `h1` en `--t-2xl`/600, `h2` de section en `--t-l`/600, `h3` de carte en `--t-m`/600, libellés de champ en `--t-s`/500, méta en `--t-xs` couleur `--discret`. Interlignage 1.5 pour le corps, 1.2 pour les titres. Prose (`.prose`) : `max-width: 65ch`.
- **Boutons : classes sur `<button>` natif.** Une classe `.btn`, avec la variante primaire par défaut et deux modificateurs, `.btn-secondaire` et `.btn-discret`. Hauteur minimale 2.25rem (le minimum exigé est 24 px, 36 px est plus confortable). États `:hover`, `:active`, `:disabled` et `[aria-busy="true"]` (curseur d'attente, opacité). Le focus reste `:focus-visible` 3px `--accent`.
- **État « en cours » partagé.** Un seul `SubmitFunction` dans `web/src/lib/envoi.ts` : il pose `disabled` et `aria-busy` sur `submitter`, puis les retire après `update()`. Toutes les pages passent `use:enhance={envoi}`. Sans JavaScript, rien ne change. *Alternative écartée :* un `$state` par formulaire, recopié dans chaque page.
- **Badges.** Une classe `.badge` et des modificateurs : `-score-haut` (≥ `score_min` + 15), `-score-moyen` (≥ `score_min`), `-score-bas`, `-avertissement` et `-statut-{groupe}`. Le texte reste toujours présent, la couleur ne porte jamais seule l'information. Le seuil vient de la configuration, déjà lue côté serveur.
- **Mouvement.** Transitions de 150 à 200 ms sur la couleur et l'ombre seulement. Un bloc `@media (prefers-reduced-motion: reduce)` ramène toute `transition` et toute `animation` à 0.01ms.
- **Preuve d'accessibilité : `@axe-core/playwright`.** Ajouté à `a11y.spec.ts`, il boucle sur les six URL et les deux thèmes (`page.emulateMedia({ colorScheme })`) avec les tags `wcag2a`, `wcag2aa`, `wcag21a` et `wcag21aa`. Le contrôle de contraste maison est gardé, car il cible des éléments précis et donne un message en français.
- **Garde contre les couleurs littérales.** Un test Vitest parcourt `web/src/**/*.svelte` et échoue sur un hexadécimal, `rgb(` ou `hsl(`. C'est ce qui rend la requirement *Design tokens only* vérifiable.

## Risks / Trade-offs

- [Renommer des classes casse les sélecteurs de `a11y.spec.ts` et `suivi.spec.ts`] → garder les noms existants quand c'est possible (`.puces`, et `.etiquette` en alias de `.badge`), et mettre à jour les sélecteurs dans le même lot.
- [`axe` trouve des violations invisibles aujourd'hui] → les corriger dans ce lot. Pour un faux positif, exclure la règle visée sur l'élément visé, avec la raison en commentaire, jamais par un `disableRules` global.
- [Poids des polices ≈ 100 Ko] → sous-ensemble latin et quatre fichiers seulement, servis en local, sans coût réseau.
- [Bleu pétrole jugé moins « cliquable » que le bleu standard] → les liens restent soulignés et les boutons primaires ont un fond plein.

## Résultats du lot 1

- 1.3 : `axe` sur le code d'avant C8 trouve une seule règle en échec, `label-content-name-mismatch` (WCAG 2.5.3) sur `/entreprises`, dans les deux thèmes : le bouton affiche « Écartée » mais son nom accessible est « Écarter {nom} ». Corrigé en 1.6 en affichant « Écarter », qui est contenu dans le nom. Les cinq autres pages passent. Mutation : sans `<label>` autour du filtre Piste, `select-name` fait échouer le test.
- 1.4 : la palette finale garde les neutres chauds et passe l'accent au bleu pétrole : `#155e75` en clair (survol `#0e4757`), `#67c6dd` en sombre. `ui-ux-pro-max` (`--domain color`, « job board ») propose aussi un bleu froid foncé pour l'action (`#0369A1`), ce qui confirme la famille ; ses autres palettes sont des valeurs Tailwind par défaut, écartées. Sémantiques en clair : succès `#2f6f3e`, avertissement `#8a5300`, danger `#b42318` ; en sombre : `#85d197`, `#f0b459`, `#ff9b8f` ; chacune a un fond teinté pour les badges. Les badges utilisent des modificateurs par ton (`.succes`, `.avertissement`, `.danger`, `.en-cours`, `.positif`, `.clos`) et non par score : le passage du score au ton se fera là où le seuil est connu (changes suivants). Les primitives sont les valeurs de `:root`, sans couche intermédiaire, puisque rien d'autre ne les lit. Contraste maison et `axe` verts dans les deux thèmes (27 tests).
- 1.5 : Plex Sans (400, 500, 600) et Plex Mono (400), sous-ensemble latin, importées dans `+layout.svelte`. Le test `e2e/design.spec.ts` vérifie qu'elles sont chargées et qu'aucune requête ne quitte `127.0.0.1` ; un `@import` Google Fonts le fait échouer.
- 1.6 : boutons stylés sur `<button>` lui-même (primaire par défaut), plus `.btn-secondaire` et `.btn-discret`, au lieu d'une classe `.btn` à poser partout. `envoi.ts` reconnaît le bouton par la présence de `disabled` (et non par `instanceof`), ce qui le rend testable en Vitest sans navigateur. Un bouton marqué « Contactée » disparaît après la réponse, donc sa libération est prouvée en Vitest (y compris quand `update()` échoue) ; Playwright prouve l'état occupé pendant une requête retenue, puis l'absence de tout `aria-busy`. Mutations : ne pas retirer `aria-busy` → Vitest rouge ; `use:enhance` sans `envoi` → Playwright rouge. Le bouton « Écartée » de `/entreprises` affiche désormais « Écarter » (violation `axe` de 1.3).
- 1.7 : à 375 px, `/entreprises`, `/offres`, `/stats`, `/projet` et la fiche ne débordent pas : les tableaux défilent dans `.defile`. Le test était vert dès le premier passage ; mutation : `min-width: 40rem` sur `main` → rouge.
- 1.8 : revue `web-design-guidelines` (règles Vercel, 104 points). Appliqué : `text-wrap: balance` sur les titres, `touch-action: manipulation` sur les éléments cliquables, `<meta name="theme-color">` clair et sombre dans `app.html` ; `transition: all` absent, `<select>` déjà avec fond et couleur explicites, `color-scheme` posé. Écarté : Title Case et deuxième personne (règles anglaises, page projet volontairement à la première personne), préchargement des polices (servies en local) et virtualisation des listes (50 lignes par page). Reporté : espaces insécables dans « 12 km », confirmation ou annulation de « Écarter », badge « sous le seuil » collé au score (`dashboard-listes-et-fiches`). `browser-proof` : 12 captures relues à côté de `docs/captures/avant-c8/`. La Mono rendait les cellules de nombres plus grandes que leurs voisines, à cause du `font-size: 0.95em` de `.donnee` qui l'emportait sur celui de `td` : la réduction ne vaut plus que pour `span.donnee`. La Mono est retirée des valeurs de la fiche, isolées et sans colonne à aligner. Restent pour les changes suivants, comme prévu : le kanban (colonnes hors écran, formulaire par carte), le mur de boutons « Contactée » et les tuiles des statistiques.
- 1.9 : gate verte. Web : `npm run check` sans erreur (`SubmitFunction` vient de `$app/forms` en SvelteKit 3), 152 Vitest, build, 51 Playwright (35 avant le lot). Python : ruff, mypy, 721 pytest.
