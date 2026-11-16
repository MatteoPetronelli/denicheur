# Tasks

## 1. Lot 1 : modèle de suivi (skills : database-design, tdd-workflow)

- [x] 1.1 `marquer(session, offre_id, statut, now)` : création au premier marquage, table de transitions, `TransitionInvalide`, offre inconnue refusée, statut identique sans effet. Vérifié par `tests/test_tracking.py` (une ligne par offre, `envoyee_le` conservé, base inchangée après refus) et mutation : retirer la vérification de transition → test rouge.
- [x] 1.2 `candidatures_a_relancer(session, today)` : statut `candidature_envoyee`, 7 jours révolus, `rappel_le` vide. Vérifié par tests J+7 / J+6 / déjà rappelée et mutation : remplacer `<=` par `<` → rouge.
- [x] 1.3 `stats(session)` : comptes par statut, nouvelles sans suivi, rejets. Vérifié par un test sur une base peuplée.
- [x] 1.4 Gate complète verte (`ruff format --check`, `ruff check`, `mypy src`, `pytest -q`) et `graphify update .`.

## 2. Lot 2 : bot en polling (skills : threat-modeling, tdd-workflow, mutation-verified-testing)

- [x] 2.1 Étape bloquante : script jetable dans le scratchpad (`deleteWebhook`, message avec bouton de test, appui de l'utilisateur, `getUpdates` brut). Consigner dans `design.md` la forme de `callback_query` et le comportement de l'offset. Vérifié par la section ajoutée à `design.md`.
- [x] 2.2 `telegram/keyboard.py` : constructeur du clavier et analyse stricte de la donnée de bouton. Vérifié par tests (formes valides, `zzz`, longueur ≤ 64 octets).
- [x] 2.3 Textes français et réponses dans `messages_fr.py` (échappement HTML, coupure 4096). Vérifié par tests dont le titre hostile.
- [x] 2.4 `telegram/commands.py` : `/aujourdhui /stage /alternance /candidatures /relances /stats /pause /reprendre /config` et commande inconnue. Vérifié par tests (effet en base et texte) ; `/config` sans secret.
- [x] 2.5 `telegram/bot.py` : `boucle(deps, *, sleep, continuer)` avec liste blanche, garde `update_id`, `dernier_update_id`, callbacks `p/b/r/x`, `answerCallbackQuery` toujours, erreurs isolées par update, erreur réseau sans arrêt. Vérifié par tests (chat étranger → 0 appel API, doublon ignoré, redémarrage au bon offset, update défectueuse dépassée).
- [x] 2.6 Mutation-vérifier la liste blanche (messages et boutons) et la garde `update_id` : casser, voir rouge, restaurer.
- [x] 2.7 Sous-commande `bot` dans `__main__.py` (message d'aide et code 1 sans jeton ou sans chat). Vérifié par test CLI.
- [x] 2.8 `scripts/installer_taches.ps1` : tâche « à l'ouverture de session » pour le bot, redémarrage sur échec, une instance, réinstallable. Vérifié en relisant le script ; l'enregistrement est lancé par l'utilisateur avec `!`.
- [x] 2.9 Gate complète verte et `graphify update .`. Fini quand « ✅ Je postule » sur le téléphone met à jour `denicheur.db` (vérification réelle avec l'utilisateur).

## 3. Lot 3 : boutons sur les offres envoyées et rappel J+7

- [ ] 3.1 `envoyer_digest` et l'alerte instantanée joignent le clavier ; en-têtes et messages de test sans clavier. Vérifié par tests sur `MockTransport` (corps de requête).
- [ ] 3.2 Étape de rappel dans `executer` : fenêtre 08:00–20:00, `pause`, `rappel_le` renseigné après envoi, texte français. Vérifié par tests : rappel à J+7, pas à J+6, pas deux fois, pas en pause, un échec d'envoi laisse la candidature due.
- [ ] 3.3 Mutation-vérifier la règle « une seule fois » (retirer l'écriture de `rappel_le`) et le seuil J+7.
- [ ] 3.4 Gate complète verte, `openspec validate bot-interactif --strict`, `graphify update .`. Fini quand une candidature antidatée déclenche un seul rappel.

## 4. Clôture

- [ ] 4.1 Mettre à jour `README.md` (commande `bot`, tâche de session, boutons) et `CLAUDE.md` (statut). Vérifié par relecture.
- [ ] 4.2 Archiver avec `openspec archive bot-interactif --yes` ; `openspec validate --specs --strict` vert.

## Workflow follow-up

- Prérequis humain avant 2.9 : autoriser et lancer l'installation de la tâche du bot (`! powershell -ExecutionPolicy Bypass -File scripts/installer_taches.ps1`).
- Un lot à la fois ; commits Conventional Commits sans trailer IA ; demander avant de pousser.
