# Design

## Context

Voir `proposal.md` pour la motivation. État du code observé avant ce plan :

- `candidatures` porte déjà `entreprise_id` (entier sans clé étrangère, commentaire « FK ajoutée en C6 ») et `offre_id` facultatif ; `brouillons.candidature_id` est obligatoire. Il n'y a pas d'index unique sur `candidatures.offre_id` (raccourci assumé : un seul écrivain à la fois).
- Le suivi (`repo.marquer`, `verifier_brouillon`, `enregistrer_brouillon`, `lire_brouillon`) est écrit autour d'une offre. `BrouillonLu.offre_id` est un entier obligatoire et le bot (`_deposer`, `_rediger`) appelle `lire_offre` sur lui.
- La rédaction (`Redacteur.rediger(offre, score, type_)`), `documents.rendre_lettre/ecrire_lettre`, `gmail_drafts.sujet_brouillon` et `messages_fr.message_accompagnement` prennent une `Offre` (titre = poste). Le type `spontanee` (120–180 mots) existe dans les prompts mais aucun bouton ne l'utilise.
- Le digest part dans `pipeline/run._notifier` une fois par jour (paramètre `dernier_digest`) ; `collecter_recruteurs` renvoie les recruteurs LBA mais personne ne les lit.
- Le CSV compte 150 entreprises (rang 1 à 150, SIRET unique, colonnes `statut`, `date_contact`, `notes` toutes vides). Les recruteurs LBA de la fixture n'ont ni adresse e-mail (`recipient_id` nul) ni téléphone : aucune source ne fournit de destinataire.
- Vérifié le 2026-11-18 : `GET /near_point?lat=48.88&long=2.0775&radius=25&activite_principale=62.01Z` répond 200 ; `/search` refuse `lat` et `long` (400 : « ne sont autorisés que pour une recherche géographique »). La réponse contient des `dirigeants` (noms, année et mois de naissance), la tranche d'effectif en code INSEE (`"12"`, `"51"`) et une liste `matching_etablissements`.

## Goals / Non-Goals

**Goals:**
- Réutiliser le flux de C5 (rédaction, lettre PDF et DOCX, brouillon Gmail) pour une entreprise sans le dupliquer.
- Ne pas casser les offres : les fonctions et tests existants pour une offre restent valables.
- Garder les trois sources d'entreprises indépendantes : une panne de l'une ne bloque ni les autres ni le digest.

**Non-Goals:**
- Trouver ou deviner des adresses e-mail, scraper un site, ou envoyer quoi que ce soit.
- Relancer une entreprise, détecter une réponse (la relance reste réservée aux offres).
- Interface de gestion des entreprises : le tableau de bord est C7.

## Decisions

1. **Suivi d'une entreprise = une ligne `candidatures` avec `offre_id` nul et `entreprise_id` renseigné.** Les statuts, `envoyee_le` et les brouillons existants servent tels quels, `brouillons` ne change pas. Alternatives : une table de suivi séparée (doublon des statuts et du stockage des brouillons) ; rendre `brouillons.candidature_id` nul et ajouter `entreprise_id` (casse l'invariant « un brouillon appartient à un suivi »). Un index unique sur `candidatures.entreprise_id` (les NULL multiples sont permis par SQLite) donne la garantie « un suivi par entreprise » qui manque aux offres. La clé étrangère s'ajoute par `batch_alter_table` (SQLite ne sait pas ajouter une clé étrangère par `ALTER`) : la table est recopiée avec ses données, ce que la migration teste sur une base `0001` remplie. Aucun `CHECK` « une seule cible » : la règle est tenue par `repo`.

2. **Table `entreprises`** : `id`, `siret` (unique), `nom`, `activite`, `naf`, `effectif` (texte lisible type « 10-19 »), `adresse`, `commune`, `lat`, `lon`, `distance_km`, `priorite` (entier nul), `url_candidature`, `origine` (`csv`, `lba`, `sirene`), `listee_le`, `contactee_le`, `ignoree_le`, `cree_le`, `maj_le`. Un upsert par SIRET met à jour uniquement les champs descriptifs ; `priorite` n'est écrasée que par le CSV (le CSV est la liste voulue par l'utilisateur) ; `listee_le`, `contactee_le` et `ignoree_le` ne sont jamais touchées par une source. Aucune colonne pour les dirigeants : le mapping de la réponse API ne lit pas ce champ.

3. **Généraliser `repo` par une cible interne, pas par des doublons.** Un petit objet privé décrit la colonne de `candidatures` visée (`offre_id` ou `entreprise_id`) et l'erreur « inconnue » (`OffreInconnue` ou `EntrepriseInconnue`). `marquer`, `verifier_brouillon`, `enregistrer_brouillon` s'écrivent une fois sur cette cible ; les fonctions publiques actuelles gardent leur signature et ajoutent des pendants `*_entreprise`. `BrouillonLu` reçoit `entreprise_id` en plus d'un `offre_id` devenu facultatif. Alternative écartée : copier-coller les quatre fonctions (la relance unique et les refus divergeraient avec le temps).

4. **Cible de rédaction.** `documents`, `gmail_drafts` et le message d'accompagnement passent d'une `Offre` à un petit objet `Cible(entreprise, poste)` (poste vide pour une spontanée) avec un constructeur depuis une offre ; les tests existants sont adaptés mécaniquement. `Redacteur` gagne `rediger_entreprise(entreprise, type_)` qui partage avec `rediger` la boucle d'essai, le nettoyage et le contrôle de longueur ; seuls les messages utilisateur diffèrent. Le message système ne change pas (mêmes trois fichiers de profil, mêmes règles : aucune donnée personnelle).

5. **Prompt d'entreprise.** Il donne nom, activité (libellé NAF), commune, la disponibilité en alternance et la consigne « tu ne sais rien d'autre de cette entreprise ; n'invente aucun produit, client ni chiffre ». Sans score, il n'y a pas de « projet à citer » : le modèle choisit dans le profil le projet le plus proche de l'activité, et la ligne « Éléments du profil utilisés » permet de vérifier. Le texte sans trou est garanti comme en C5 (retrait de tout « […compléter…] »).

6. **Entreprises de l'API publique.** Appel par code NAF avec `per_page=25` et une pagination bornée (3 pages au plus par code : 75 entreprises, bien plus que ce qu'une liste de 10 par jour consomme). On lit `matching_etablissements` (l'établissement proche du centre) plutôt que `siege`, qui peut être à Strasbourg pour un groupe national : SIRET, adresse et coordonnées viennent de l'établissement, le nom de l'unité légale. La distance se calcule avec `haversine_km` existant. La tranche d'effectif se convertit du code INSEE vers un libellé ; les codes 32 et au-delà (250 salariés et plus) sont écartés, un effectif inconnu est gardé. L'étape bloquante du Lot 2 vérifie ces champs sur une vraie réponse avant d'écrire le mapping et enregistre une fixture amputée des dirigeants. Les recruteurs LBA sont filtrés sur les mêmes codes NAF et la même taille.

7. **Liste du jour et actualisation.** L'actualisation (LBA puis API, chacune isolée) tourne une fois par jour Paris dans le run (paramètre `derniere_actualisation:entreprises`, même schéma que la collecte de stages). La liste part dans `_notifier` juste après le digest, sous la même condition horaire, avec son paramètre `derniere_liste_entreprises` ; chaque entreprise est marquée `listee_le` et validée en base dès l'envoi de son message, comme les offres. La requête de sélection trie `priorite` avec les valeurs nulles à la fin, puis `distance_km`, puis `id`, et limite à `entreprises.liste_par_jour`. Le plafond de brouillons se compte en base (brouillons d'entreprise créés dans la journée Paris), pas en mémoire : il survit au redémarrage du bot.

8. **Boutons.** Lettres nouvelles dans la regex : `s` (brouillon spontané), `t` (lettre PDF), `e` (envoyée), `i` (ignorer) ; elles désignent un identifiant d'entreprise, alors que `b`, `l`, `d`, `p`, `r`, `x` désignent une offre et `g` un brouillon (il sert aussi aux brouillons d'entreprise). Le message d'une entreprise garde le lien LBA en texte (pas de bouton URL) pour que l'utilisateur candidate par ce formulaire s'il préfère. Le dépôt Gmail d'une entreprise n'a pas de destinataire.

9. **Configuration.** Un bloc `entreprises:` dans `config/recherches.yaml` (`naf`, `effectif_max`, `liste_par_jour`, `brouillons_max_jour`, `pages_max`), avec des valeurs par défaut dans le modèle pour que les configurations de test existantes restent valides. Le rayon et le centre sont ceux du reste de la configuration.

10. **Import du CSV par commande manuelle** (`import-entreprises`), pas par le run : c'est une donnée de départ que l'utilisateur fournit, qu'il peut rejouer sans risque (upsert). Les colonnes `statut`, `date_contact`, `notes` sont ignorées (toutes vides aujourd'hui).

11. **Offre ouverte chez une entreprise listée (décision de l'utilisateur, 2026-11-18).** Une candidature spontanée montre de la motivation : une entreprise n'est jamais écartée parce qu'elle publie une offre. Le rapprochement se fait par SIRET, jamais par le nom (des noms se ressemblent). `offres` reçoit une colonne `siret` facultative (index non unique), remplie par la source La bonne alternance (`workplace.siret`, présent sur 4 offres sur 16 de la fixture) et vide pour Adzuna et les e-mails, qui ne le donnent pas. Le message d'une entreprise affiche « 📌 Offre ouverte aussi : <titre> » pour chaque offre non rejetée portant son SIRET. Les offres déjà en base ont un SIRET vide : le rapprochement ne vaut que pour les offres collectées après la migration. L'analyse d'adéquation au profil reste humaine, aidée par l'activité, l'effectif, la distance et ce rappel.

## Risks / Trade-offs

- [Migration SQLite avec recopie de table sur la base réelle] → copie de `denicheur.db` avant `init-db`, test de montée de version sur une base `0001` remplie, `downgrade` fourni.
- [La forme de la réponse de l'API change ou diffère de celle observée (établissement, effectif)] → étape bloquante de vérification sur une vraie réponse, mapping défensif (champ absent = entreprise ignorée et comptée), fixture réelle sans dirigeants.
- [Le modèle invente des détails sur une entreprise dont il ne connaît que le nom] → prompt limité au nom, à l'activité et à la commune, consigne explicite, ligne « Éléments du profil utilisés », relecture humaine ; mesure réelle au Lot 4.
- [Une entreprise listée mais jamais traitée ne revient pas] → voulu (« jamais deux fois ») ; 150 entreprises à 10 par jour couvrent 15 jours, et l'utilisateur peut toujours appuyer sur un bouton sur un ancien message.
- [Quinze lettres par jour sur un Ollama partagé avec le scoring] → plafond de 15 ; une lettre mesure environ 77 s en C5 ; la boucle de polling est déjà bloquante pendant une rédaction, comme en C5.
- [Données de dirigeants dans la réponse de l'API] → jamais lues par le mapping, test qui parcourt toutes les valeurs stockées avec un nom de dirigeant de la fixture.
- [Un établissement proche appartient à un groupe de plus de 250 salariés] → le filtre d'effectif s'applique à l'unité légale ; un effectif inconnu est gardé et relu par l'utilisateur.

## Migration Plan

1. Copier `denicheur.db` (sauvegarde locale hors git).
2. `py -m denicheur init-db` applique la révision `0002` (table `entreprises`, clé étrangère et index unique sur `candidatures.entreprise_id`).
3. `py -m denicheur import-entreprises entreprises_spontanees_mareil-marly.csv`.
4. Redémarrer le bot avec le nouveau code (arrêter uniquement son processus, puis `Start-ScheduledTask -TaskName DenicheurBot`) après les Lots 3 et 4.
5. Retour arrière : restaurer la copie de la base ; `downgrade` supprime la table et l'index sans toucher aux offres.

## Open Questions

- Où trouver une adresse e-mail de recrutement par entreprise : hors périmètre ; le lien LBA du CSV sert de canal.

## Résultat de la mesure

**Lot 1 (2026-11-18).** Sauvegarde cohérente par l'API de sauvegarde SQLite (`denicheur-avant-c6.db`, ignorée par git). Comptes avant : 198 offres, 105 scores, 15 candidatures, 4 brouillons. Après `init-db` (révision `0002`) : mêmes comptes, `PRAGMA integrity_check` = ok, clé étrangère `candidatures.entreprise_id -> entreprises.id` présente. Premier import du CSV : 150 créées, 0 ignorée ; second import : 0 créée, 150 mises à jour. Priorités 1 à 150, 150 SIRET distincts, 150 liens de candidature spontanée, 148 communes lues (deux adresses sans code postal), distances de 1,5 à 11,2 km.

