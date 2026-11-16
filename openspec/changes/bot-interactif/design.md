# Design

## Context

- `TelegramAPI` (lié à un seul chat) offre déjà `send_message(reply_markup)`, `answer_callback`, `edit_keyboard`, `delete_webhook`, `get_updates(offset, timeout)`. Aucun bouton n'est encore envoyé.
- `candidatures` existe (statut, `envoyee_le`, `rappel_le`, `relance_le`, `notes`, `cree_le`, `maj_le`) : pas de migration. `parametres` porte déjà `pause` ; on y ajoute `dernier_update_id`.
- `run` (Planificateur, toutes les heures) et le bot (processus long) écrivent dans la même base SQLite en WAL.
- Le bot est le premier point d'entrée externe : tout ce qui arrive de Telegram est une entrée non fiable. Voir « Modèle de menaces ».

## Goals / Non-Goals

**Goals:**
- Marquer une offre depuis le téléphone et le retrouver dans `denicheur.db`.
- Rappel J+7 une seule fois.
- Un bot qui ne s'arrête jamais de lui-même et ne réagit qu'à son propriétaire.

**Non-Goals:**
- Brouillons (C5) : le bouton répond seulement qu'ils arriveront. Relance envoyée (`relancee`) : transition prévue, mais pas de bouton avant C5.
- Webhook, serveur public, plusieurs utilisateurs.
- Édition de la config depuis Telegram (`/config` est en lecture seule).

## Decisions

1. **Suivi dans `repo`, transitions dans une table de données.** `marquer(session, offre_id, statut, now)` crée la ligne au premier marquage, lève `TransitionInvalide` hors table, ne fait rien si le statut est identique (conserve `envoyee_le`). Alternative écartée : machine à états en classes, trop lourd pour 9 statuts.
2. **« Nouvelle » = absence de ligne.** Pas de ligne `nouvelle` en base : le digest n'a pas à créer de suivi. `nouvelle → candidature_envoyee` est permis directement : « Je postule » doit marcher sans passer par « intéressée ». La feuille de route listait la chaîne `nouvelle→interessante→…` ; `interessante` reste facultative.
3. **Bouton « Rappel » = `interessante`.** Le rappel J+7 se calcule à partir de `envoyee_le`, donc avant d'avoir postulé il n'y a rien à planifier : « Rappel » garde l'offre en liste d'attente (visible dans `/candidatures`). Hypothèse à confirmer par l'utilisateur ; sans conséquence sur le schéma.
4. **Données de bouton `<lettre>:<offre_id>`** (`p`, `b`, `r`, `x`), analysées par une fonction pure ; tout ce qui ne correspond pas à `^[pbrx]:\d{1,9}$` reçoit la réponse neutre. Alternative écartée : JSON (plus long, rien à gagner dans 64 octets).
5. **Clavier construit une seule fois** (`telegram/keyboard.py`) et passé par `envoyer_digest` et l'alerte instantanée ; après « Je postule », `edit_keyboard` le remplace par un seul bouton inerte « ✅ Envoyée ».
6. **Polling dans un module testable.** `boucle(deps, *, sleep, continuer)` : `continuer` (rappel booléen, vrai par défaut) permet aux tests de borner les tours ; `sleep` est injecté. Un tour = `get_updates(offset=dernier+1, timeout=50)` puis traitement dans l'ordre ; `dernier_update_id` est écrit **après** chaque update traitée. Le traitement est un `try/except Exception` par update : une update défectueuse est journalisée (type seulement) et dépassée, sinon elle bloquerait la file pour toujours.
7. **Rappel J+7 dans `run`**, pas dans le bot : le bot peut être éteint, `run` rattrape. Fenêtre 08:00–20:00 Paris, supprimé par `pause` sans renseigner `rappel_le` (le rappel part au premier run suivant).
8. **Texte des réponses dans `messages_fr.py`**, valeurs dynamiques via `html.escape`, coupure à 4096.
9. **Tâche planifiée du bot** : déclencheur « à l'ouverture de session », redémarrage sur échec, une instance. Enregistrée par l'utilisateur avec `!` (le harnais refuse d'enregistrer une tâche).

## Modèle de menaces

| Menace | Contrôle | Test |
|---|---|---|
| Un tiers écrit au bot (le nom est public) | Liste blanche sur `chat.id` pour messages **et** `callback_query` ; aucun appel API pour un chat étranger | chat étranger → 0 appel, base inchangée (mutation : retirer la garde) |
| Rejeu / doublon d'update | `update_id ≤ dernier_update_id` ignoré | doublon → une seule action (mutation : retirer la garde) |
| Donnée de bouton forgée ou malformée | Regex stricte, offre vérifiée en base | `zzz`, id inexistant → réponse neutre, base inchangée |
| Contenu d'offre hostile dans une réponse | `html.escape` systématique | titre `<b>` échappé |
| Fuite du jeton | `TelegramError` sans URL ; journaux sans jeton | message d'erreur sans jeton |
| Boucle bloquée par une update défectueuse | `try/except` par update, offset avancé | update qui lève → la suivante passe |
| Écritures concurrentes `run` / bot | WAL, transactions courtes, commit après chaque action | — |

## Risks / Trade-offs

- [La forme réelle de `callback_query` et l'effet de l'offset diffèrent de la doc] → étape bloquante du lot 2 : script jetable avec le vrai bot, résultat noté ici avant d'écrire `bot.py`.
- [Le bot est éteint (PC éteint) : les appuis attendent] → Telegram garde les mises à jour 24 h ; elles sont rejouées dans l'ordre au redémarrage.
- [Le long polling (50 s) et `get_updates` fixent `timeout=60` côté `httpx`] → l'API actuelle est appelée avec `timeout=60` : marge suffisante, à vérifier à l'expérience.
- [`/pause` modifie `pause` pendant qu'un `run` tourne] → le run lit `pause` à chaque envoi ; pas de verrou, effet au prochain envoi.
- [`dernier_update_id` perdu si la base est recréée] → le bot reçoit d'anciennes updates : sans danger, les actions sont idempotentes.

## Open Questions

- « Rappel » = `interessante` (décision 3) : à confirmer à l'usage ; changer ce comportement ne touche pas le schéma.
