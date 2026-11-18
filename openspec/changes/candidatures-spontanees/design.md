# Design

## Context

Voir `proposal.md` pour la motivation. État du code observé avant ce plan :

- `candidatures` porte déjà `entreprise_id` (entier sans clé étrangère, commentaire « FK ajoutée en C6 ») et `offre_id` facultatif ; `brouillons.candidature_id` est obligatoire. Il n'y a pas d'index unique sur `candidatures.offre_id` (raccourci assumé : un seul écrivain à la fois).
- Le suivi (`repo.marquer`, `verifier_brouillon`, `enregistrer_brouillon`, `lire_brouillon`) est écrit autour d'une offre. `BrouillonLu.offre_id` est un entier obligatoire et le bot (`_deposer`, `_rediger`) appelle `lire_offre` sur lui.
- La rédaction (`Redacteur.rediger(offre, score, type_)`), `documents.rendre_lettre/ecrire_lettre`, `gmail_drafts.sujet_brouillon` et `messages_fr.message_accompagnement` prennent une `Offre` (titre = poste). Le type `spontanee` (120–180 mots) existe dans les prompts mais aucun bouton ne l'utilise.
- Le digest part dans `pipeline/run._notifier` une fois par jour (paramètre `dernier_digest`) ; `collecter_recruteurs` renvoie les recruteurs LBA mais personne ne les lit.
- Le CSV compte 150 entreprises (rang 1 à 150, SIRET unique, colonnes `statut`, `date_contact`, `notes` toutes vides). Les recruteurs LBA de la fixture n'ont ni adresse e-mail (`recipient_id` nul) ni téléphone : aucune source ne fournit de destinataire.
- Vérifié le 2026-11-18 (OpenAPI de l'API et appels réels) : `/near_point` répond 200 mais n'accepte que `lat`, `long`, `radius` (≤ 50 km), `activite_principale`, `section_activite_principale`, `limite_matching_etablissements`, `page`, `per_page` (≤ 25) et `sort_by_size` : aucun filtre d'effectif ni d'état (les paramètres inconnus sont ignorés en silence), `total_results` plafonné à 10 000, plus de 10 000 unités de NAF 62.01Z dans 25 km, ordre non géographique, jusqu'à 10 établissements correspondants par unité dont des fermés. `/search` refuse `lat` et `long` (400) mais filtre par `departement`, `activite_principale`, `tranche_effectif_salarie` et `etat_administratif` : pour 10 à 249 salariés, 369 unités dans les Yvelines, 148 dans le Val-d'Oise, 1 691 dans les Hauts-de-Seine, plus de 2 000 à Paris, tous NAF confondus parmi les quatre. La réponse contient des `dirigeants` (noms, année et mois de naissance), la tranche d'effectif en code INSEE (`"12"`, `"51"`) et une liste `matching_etablissements` avec latitude et longitude.

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

6. **Entreprises de l'API publique : `/search` par département, pas `near_point`.** L'appel interroge `/search` pour chaque couple (département configuré, code NAF) avec `etat_administratif=A`, les tranches d'effectif INSEE comprises entre `effectif_min` (10) et `effectif_max` (249) et `per_page=25`. Les départements par défaut sont 78, 92, 95 et 75, ceux qui touchent un rayon de 25 km autour de Mareil-Marly. Pour chaque unité, le code garde parmi `matching_etablissements` et le siège les établissements en activité avec coordonnées, choisit le plus proche du centre (`haversine_km` existant) et ne conserve l'unité que si cette distance est dans `rayon_km` : SIRET, adresse et coordonnées viennent de cet établissement, le nom de l'unité légale, l'activité du libellé NAF de l'unité (table locale des quatre codes, le code sinon). Alternative écartée : `near_point`, trop bruité (voir Context). Comme chaque couple contient jusqu'à 50 pages, un curseur par couple (`curseur_entreprises:<département>:<naf>` dans `parametres`) avance de `pages_max` pages à chaque actualisation et revient à la page 1 après la dernière : tout est couvert en quelques semaines sans centaines d'appels par jour (au plus 16 couples × 3 pages = 48 appels, espacés de 0,2 s sous la limite de 7 appels par seconde). Une même unité légale (même SIREN, c'est-à-dire les 9 premiers chiffres du SIRET) n'est enregistrée qu'une fois : une source autre que le CSV ne crée pas une entreprise dont le SIREN existe déjà. Le libellé d'effectif d'une unité vient de la tranche INSEE (« 20-49 »). L'étape bloquante du Lot 2 a enregistré une fixture réelle amputée des dirigeants. Les recruteurs LBA sont filtrés sur les mêmes codes NAF et la même taille maximale.

7. **Liste du jour et actualisation.** L'actualisation (LBA puis API, chacune isolée) tourne une fois par jour Paris dans le run (paramètre `derniere_actualisation:entreprises`, même schéma que la collecte de stages). La liste part dans `_notifier` juste après le digest, sous la même condition horaire, avec son paramètre `derniere_liste_entreprises` ; chaque entreprise est marquée `listee_le` et validée en base dès l'envoi de son message, comme les offres. La requête de sélection trie `priorite` avec les valeurs nulles à la fin, puis `distance_km`, puis `id`, et limite à `entreprises.liste_par_jour`. Le plafond de brouillons se compte en base (brouillons d'entreprise créés dans la journée Paris), pas en mémoire : il survit au redémarrage du bot.

8. **Boutons.** Lettres nouvelles dans la regex : `s` (brouillon spontané), `t` (lettre PDF), `e` (envoyée), `i` (ignorer) ; elles désignent un identifiant d'entreprise, alors que `b`, `l`, `d`, `p`, `r`, `x` désignent une offre et `g` un brouillon (il sert aussi aux brouillons d'entreprise). Le message d'une entreprise garde le lien LBA en texte (pas de bouton URL) pour que l'utilisateur candidate par ce formulaire s'il préfère. Le dépôt Gmail d'une entreprise n'a pas de destinataire.

9. **Configuration.** Un bloc `entreprises:` dans `config/recherches.yaml` (`naf`, `departements`, `effectif_min`, `effectif_max`, `liste_par_jour`, `brouillons_max_jour`, `pages_max`), avec des valeurs par défaut dans le modèle pour que les configurations de test existantes restent valides. Le rayon et le centre sont ceux du reste de la configuration.

10. **Import du CSV par commande manuelle** (`import-entreprises`), pas par le run : c'est une donnée de départ que l'utilisateur fournit, qu'il peut rejouer sans risque (upsert). Les colonnes `statut`, `date_contact`, `notes` sont ignorées (toutes vides aujourd'hui).

11. **Offre ouverte chez une entreprise listée (décision de l'utilisateur, 2026-11-18).** Une candidature spontanée montre de la motivation : une entreprise n'est jamais écartée parce qu'elle publie une offre. Le rapprochement se fait par SIRET, jamais par le nom (des noms se ressemblent). `offres` reçoit une colonne `siret` facultative (index non unique), remplie par la source La bonne alternance (`workplace.siret`, présent sur 4 offres sur 16 de la fixture) et vide pour Adzuna et les e-mails, qui ne le donnent pas. Le message d'une entreprise affiche « 📌 Offre ouverte aussi : <titre> » pour chaque offre non rejetée portant son SIRET. Les offres déjà en base ont un SIRET vide : le rapprochement ne vaut que pour les offres collectées après la migration. L'analyse d'adéquation au profil reste humaine, aidée par l'activité, l'effectif, la distance et ce rappel.

## Risks / Trade-offs

- [Migration SQLite avec recopie de table sur la base réelle] → copie de `denicheur.db` avant `init-db`, test de montée de version sur une base `0001` remplie, `downgrade` fourni.
- [La forme de la réponse de l'API change ou diffère de celle observée (établissement, effectif)] → vérification sur de vraies réponses (faite le 2026-11-18), mapping défensif (champ absent = entreprise ignorée et comptée), fixture réelle sans dirigeants.
- [Un département de la liste couvre bien plus que le rayon (75, 92)] → la distance est recalculée localement et seules les entreprises dans `rayon_km` sont gardées ; les pages « perdues » coûtent des appels, pas de la qualité.
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

**Lot 2 (2026-11-18).** Actualisation réelle sur la vraie base : 42 appels à `/search` en 32 s, aucune erreur, 611 entreprises ajoutées (origine `sirene`), 611 SIREN distincts, aucune au-delà de 25 km (distances de 0,8 à 24,4 km, moyenne 15,8 km). Effectifs : 20-49 (183), 10-19 (179), 50-99 (113), 100-199 (101), 200-249 (35) ; NAF : 62.02A (192), 62.01Z (173), 58.29C (131), 63.11Z (115). Les curseurs avancent de 3 pages par couple (« 4 » ou revenu à « 1 » quand le couple n'a qu'une à trois pages). Le run horaire de 13:30 Paris a ensuite refait l'actualisation seul (une fois par jour, sans erreur), recruteurs LBA compris : 150 recruteurs lus, 114 retenus sur les NAF et la taille, un seul nouveau (les autres partagent le SIREN d'une entreprise du CSV). Après deux passages de la recherche, la base compte 1 236 entreprises (150 du CSV, 1 de LBA, 1 085 de la recherche) ; les 3 SIREN qui apparaissent deux fois viennent du CSV de l'utilisateur, qui garde chaque SIRET.

**Lot 3 (2026-11-18).** Piège trouvé en écrivant les tests : les suivis d'entreprise ont `offre_id` nul, ce qui faisait renvoyer zéro ligne à tout `NOT IN (SELECT offre_id …)` (offres du jour, meilleures offres, statistiques) et faisait planter les rappels J+7 et `/candidatures` (lecture d'une offre nulle). Les cinq requêtes écartent maintenant les lignes sans offre, et un test de non-régression les couvre. Bot redémarré avec le nouveau code (un seul processus). Première vraie liste envoyée à 13:50 Paris par `run --mode digest` : 10 entreprises de priorité 1 à 10 (de SKAIZEN GROUP à SKILLSOFT DIGITAL), marquées listées ; les boutons « Brouillon spontané » et « Lettre PDF » répondent « bientôt disponible » jusqu'au Lot 4.

