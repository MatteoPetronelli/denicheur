# Proposal

## Why

Le tableau `/` est la page la plus utilisée, et c'est la moins lisible. À 1280 px, seules quatre colonnes et demie sur huit sont visibles : « Entretien » est coupée, et « Offre reçue », « Refus » et « Sans réponse » sont hors écran sans qu'aucun indice ne le signale. Chaque carte répète « Passer à », une liste déroulante et un bouton « Changer » : ces trois éléments triplent sa hauteur et noient le titre. Les colonnes vides prennent autant de place que les pleines. Après un déplacement, le message « Statut mis à jour. » ne dit ni quoi ni où.

## What Changes

- Colonnes : toutes atteignables par un défilement horizontal aimanté, avec un en-tête collant qui porte le libellé, l'effectif et la pastille du groupe de statut. Les colonnes vides se replient en bande étroite.
- Carte compacte : le titre est un lien étiré sur toute la carte, avec l'entreprise ou l'activité et la commune, puis des badges (score coloré selon le seuil, km, piste ou priorité). Le lien externe devient une petite icône-lien avec un libellé accessible.
- Changement de statut par un menu « Déplacer » qui ne liste que les transitions permises, une action par statut, avec un nom accessible qui cite la carte. Il remplace la liste déroulante et le bouton « Changer », et marche toujours sans JavaScript.
- Retour après action : un message annoncé qui nomme la carte et son nouveau statut, puis le focus rendu à la carte dans sa nouvelle colonne.
- Barre de filtres sur une ligne, avec le bouton « Filtrer » aligné sur les champs.
- Hors périmètre : glisser-déposer, nouveaux statuts, changement des transitions (`transitions.json`), tri des cartes.

## Capabilities

### New Capabilities

### Modified Capabilities
- `dashboard-tracking` : les requirements *Kanban by status*, *Cards* et *Status change with bot rules* changent (visibilité des colonnes, carte cliquable, menu de statut, retour après action).

## Impact

- `web/src/routes/+page.svelte`, `web/src/lib/components/CarteSuivi.svelte`, `web/src/app.css` ; l'action `?/statut` de `web/src/routes/+page.server.ts` renvoie aussi le titre et le nouveau statut pour le message.
- `web/e2e/suivi.spec.ts` et `web/e2e/a11y.spec.ts` : les sélecteurs passent de « Passer à »/« Changer » au menu « Déplacer ».
- Dépend de `dashboard-fondations-visuelles` (tokens, badges, `envoi.ts`). Aucun changement côté Python ni base.
