# Tasks

Gate de chaque lot : `py -m ruff format --check .` · `py -m ruff check .` · `py -m mypy src` · `py -m pytest -q`. Fin de lot : cocher, `graphify update .`, skill `commit` (fichiers nommés, confirmation avant push).

## Lot 1 — Lecteur IMAP

Skills : `tdd-workflow`. Étape bloquante : aucune (le lecteur se teste avec un faux serveur IMAP).

- [x] 1.1 Écrire `mail/imap.py:lire_alertes(user, password, since, imap_factory=imaplib.IMAP4_SSL)` (libellé `Denicheur` en lecture seule, recherche depuis `since`, `BODY.PEEK[]`, retour de `email.message.Message`) ; vérifier avec un faux IMAP : deux messages retournés
- [x] 1.2 Garantir l'absence d'effet de bord : le faux IMAP n'accepte qu'une liste blanche de commandes (`LOGIN`, `SELECT` en lecture seule, `SEARCH`, `FETCH` avec `BODY.PEEK`, `CLOSE`, `LOGOUT`) ; vérifier que `STORE`, `COPY`, `MOVE`, `EXPUNGE` font échouer le test (mutation)
- [x] 1.3 Fermer la session même en cas d'échec et ne jamais exposer le mot de passe dans une erreur ; vérifier : `logout` appelé quand `fetch` lève, message d'erreur sans mot de passe
- [x] 1.4 Gate L1 vert (lancer les quatre commandes, noter les chiffres réels)

## Lot 2 — Analyseurs et source e-mail

Skills : `tdd-workflow`, `mutation-verified-testing`. Étape bloquante : l'utilisateur fournit 2 à 3 `.eml` anonymisés par expéditeur dans `tests/fixtures/emails/` ; ouvrir chacun et lister les blocs HTML qui portent une offre (titre, entreprise, ville, lien) avant d'écrire le moindre analyseur.

- [ ] 2.1 Écrire `mail/parsers.py` (registre par domaine de `From`, un analyseur par expéditeur avec `html.parser`, texte du bloc sans salutation ni adresse) ; vérifier : nombre d'offres attendu par fixture, expéditeur inconnu = zéro offre et une ligne de journal
- [ ] 2.2 Écrire le nettoyage de lien (paramètres de suivi, fragment) et `source_id = sha1(lien propre)` ; vérifier : même offre dans deux e-mails = un seul lien propre, une seule offre après `dedupliquer` ; mutation-vérifier la liste des paramètres retirés
- [ ] 2.3 Écrire `sources/email_alertes.py:collecter` (`Offre` avec `source="email:<site>"`, piste déduite du titre, géocodage `api-adresse` avec cache et repli `lieu_a_verifier`) ; vérifier avec `MockTransport` : un appel pour deux offres de la même commune, échec réseau = coordonnées vides sans exception
- [ ] 2.4 Gérer l'absence de `GMAIL_USER` ou `GMAIL_APP_PASSWORD` (source ignorée, journal, aucune connexion) et brancher `sources["email"]` dans `__main__._run` ; vérifier : sans mot de passe `run --dry-run` fonctionne et ne tente aucune connexion IMAP
- [ ] 2.5 Test d'invariant : aucune adresse e-mail ni nom du destinataire dans les descriptions extraites des fixtures
- [ ] 2.6 Vérification réelle : `py -m denicheur run --dry-run` avec la vraie boîte affiche des offres issues d'e-mails sans doublon, et la boîte Gmail est inchangée (aucun message marqué lu)
- [ ] 2.7 Gate L2 vert, puis mettre à jour le README (prérequis Gmail) et la ligne « Statut » de `CLAUDE.md`

## Workflow follow-up

- Archiver le changement (`openspec-archive-change`) une fois le Lot 2 validé.
- Proposer `/compact` tous les deux lots.
