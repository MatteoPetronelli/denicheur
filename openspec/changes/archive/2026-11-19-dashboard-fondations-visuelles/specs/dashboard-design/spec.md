## ADDED Requirements

### Requirement: Design tokens only
Les couleurs, espacements, tailles de texte, rayons et ombres du tableau de bord SHALL provenir d'un jeu unique de variables CSS défini pour les thèmes clair et sombre. Aucune valeur de couleur littérale SHALL apparaître dans les composants ni les pages, et une même signification SHALL toujours utiliser la même couleur (une erreur n'emprunte pas la couleur d'un avertissement).

#### Scenario: No literal colour in pages
- **WHEN** on cherche une couleur hexadécimale, `rgb(` ou `hsl(` dans les fichiers `.svelte` de `web/src`
- **THEN** aucune n'est trouvée

#### Scenario: Threshold is a warning
- **WHEN** une offre sous le seuil est affichée
- **THEN** sa mention « sous le seuil » utilise la couleur d'avertissement, pas celle d'erreur

### Requirement: Typographic hierarchy
Le tableau de bord SHALL utiliser une police d'interface et une police de données servies par l'application elle-même, sans requête vers un autre hôte. Les nombres comparés en colonne (scores, distances, effectifs, dates) SHALL utiliser des chiffres tabulaires. Les paragraphes de prose SHALL être limités à environ 65 caractères par ligne. Les titres de page, de section et de carte SHALL se distinguer par la taille ou la graisse.

#### Scenario: Fonts are local
- **WHEN** une page est chargée dans le navigateur
- **THEN** toutes les polices viennent de `127.0.0.1` et aucune requête ne part vers un autre hôte

#### Scenario: Aligned figures
- **WHEN** une colonne de scores contient 82 et 40
- **THEN** les chiffres occupent la même largeur et s'alignent

### Requirement: Interactive states
Chaque bouton et lien d'action SHALL avoir un état de survol, un état de focus visible au clavier et un état désactivé distincts. Un formulaire en cours d'envoi SHALL désactiver son bouton et l'annoncer aux technologies d'assistance jusqu'à la réponse. Les formulaires SHALL continuer de fonctionner sans JavaScript.

#### Scenario: Pending submit
- **WHEN** l'utilisateur envoie un changement de statut et que la réponse n'est pas encore arrivée
- **THEN** le bouton est désactivé et marqué occupé, puis redevient actif à la réponse

#### Scenario: Without JavaScript
- **WHEN** JavaScript est désactivé et que l'utilisateur envoie un formulaire
- **THEN** la page se recharge avec le résultat, comme avant

### Requirement: Accessibility checked by axe
Chaque page du tableau de bord SHALL passer une analyse d'accessibilité automatique (règles WCAG 2.1 A et AA) sans violation, dans les thèmes clair et sombre, et SHALL garder un contraste d'au moins 4,5:1 pour le texte.

#### Scenario: All pages clean
- **WHEN** la suite de bout en bout analyse `/`, `/entreprises`, `/offres`, `/stats`, `/projet` et une fiche, dans chaque thème
- **THEN** l'analyse ne rapporte aucune violation

### Requirement: Reduced motion
Toute transition ou animation SHALL être supprimée ou ramenée à une durée négligeable lorsque l'utilisateur demande un mouvement réduit, et aucune animation SHALL durer plus de 300 ms.

#### Scenario: Reduced motion requested
- **WHEN** le navigateur signale `prefers-reduced-motion: reduce`
- **THEN** aucun élément n'anime sa position ni son opacité

### Requirement: Readable on a small screen
À 375 px de large, chaque page SHALL être lisible sans zoom et le document SHALL ne pas défiler horizontalement ; seuls le tableau des candidatures et les tableaux de données MAY défiler dans leur propre zone. Les cibles tactiles SHALL mesurer au moins 24 × 24 px.

#### Scenario: Narrow viewport
- **WHEN** `/entreprises`, `/offres`, `/stats`, `/projet` ou une fiche est affichée à 375 px de large
- **THEN** la largeur du document ne dépasse pas celle de la fenêtre
