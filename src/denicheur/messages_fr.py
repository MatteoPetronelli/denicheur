"""Tout le texte vu par l'utilisateur (Telegram) vit ici."""

from html import escape

from denicheur.config import Config
from denicheur.db.repo import Stats
from denicheur.models import Entreprise, Offre, ScoreLLM, Statut

RIEN_DE_NEUF = "Rien de nouveau aujourd'hui"
MAX_ELEMENTS = 3
_MOIS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]  # fmt: skip


def _e(texte: str, n: int) -> str:
    """Échappe et borne un champ dynamique : la somme reste sous la limite de 4096 de Telegram."""
    return escape(texte[:n])


def entete_digest(n: int) -> str:
    return f"☀️ {n} offre{'s' if n > 1 else ''} à regarder aujourd'hui"


def _lieu(o: Offre) -> str:
    if o.lieu_a_verifier or o.distance_km is None:
        return "📍 lieu à vérifier"
    return f"📍 {_e(o.commune or 'lieu inconnu', 80)} ({o.distance_km:.0f} km)"


def _calendrier(o: Offre) -> str | None:
    morceaux = [f"{o.duree_mois} mois"] if o.duree_mois else []
    if o.debut_des_que_possible:
        morceaux.append("début : dès que possible")
    elif o.debut:
        morceaux.append(f"début : {_MOIS[o.debut.month - 1]} {o.debut.year}")
    return " · ".join(morceaux) or None


def format_offre(o: Offre, s: ScoreLLM, *, alerte: bool = False) -> str:
    """Message HTML d'une offre ; `alerte` ajoute l'en-tête d'alerte immédiate."""
    titre = f"<b>{_e(o.titre, 200)}</b>"
    lignes = [
        f"🚨 Alternance · {titre}" if alerte else titre,
        f"🏢 {_e(o.entreprise or 'entreprise non précisée', 100)} · {_lieu(o)}",
        f"🕒 {c}" if (c := _calendrier(o)) else None,
        f"⭐ Score {s.score}/100",
        "✅ " + ", ".join(_e(p, 150) for p in s.points_forts[:MAX_ELEMENTS]) if s.points_forts else None,
        "➖ " + ", ".join(_e(p, 150) for p in s.points_faibles[:MAX_ELEMENTS]) if s.points_faibles else None,
        f"⚠️ {_e(s.alerte, 300)}" if s.alerte else None,
        f"💡 Projet à citer : {_e(s.projet_a_citer, 100)}",
        f'🔗 <a href="{escape(o.url)}">Voir l\'offre</a>',
    ]
    return "\n".join(ligne for ligne in lignes if ligne)


def entete_entreprises(n: int) -> str:
    return f"🏢 {n} entreprise{'s' if n > 1 else ''} à démarcher aujourd'hui"


def format_entreprise(e: Entreprise, offres: list[str]) -> str:
    """Message HTML d'une entreprise à démarcher ; `offres` : titres des offres ouvertes de même SIRET."""
    taille = f"{_e(e.effectif, 20)} salariés" if e.effectif else None
    activite = " · ".join(x for x in (_e(e.activite, 150) if e.activite else None, taille) if x)
    commune = _e(e.commune, 80) if e.commune else None
    if e.distance_km is None:
        lieu = commune
    else:
        km = f"{e.distance_km:.0f} km"
        lieu = f"{commune} ({km})" if commune else km
    lien = (
        e.url_candidature
        if e.url_candidature and e.url_candidature.startswith(("https://", "http://"))
        else None
    )
    lignes = [
        f"🏢 <b>{_e(e.nom, 150)}</b>",
        f"💼 {activite}" if activite else None,
        f"📍 {lieu}" if lieu else None,
        f'🔗 <a href="{escape(lien[:300])}">Candidature spontanée</a>' if lien else None,
        *(f"📌 Offre ouverte aussi : {_e(titre, 150)}" for titre in offres[:MAX_ELEMENTS]),
    ]
    return "\n".join(ligne for ligne in lignes if ligne)


def echec_collecte(type_erreur: str) -> str:
    return f"⚠️ La collecte du jour a échoué : {type_erreur}"


LIMITE_TELEGRAM = 4096
AIDE = "\n".join(
    [
        "Commandes :",
        "/aujourdhui · offres du jour",
        "/stage · meilleurs stages",
        "/alternance · meilleures alternances",
        "/candidatures · suivi en cours",
        "/relances · à relancer",
        "/stats · chiffres",
        "/pause · /reprendre · envois",
        "/config · réglages",
    ]
)
AUCUNE_CANDIDATURE = "Aucune candidature suivie pour l'instant."
AUCUNE_RELANCE = "Aucune relance à faire."
PAUSE_ACTIVEE = "⏸️ Pause : le Dénicheur collecte mais n'envoie plus rien."
PAUSE_LEVEE = "▶️ Reprise : les envois repartent."
# Réponses aux boutons (fenêtre contextuelle de Telegram, 200 caractères au plus).
CB_ENVOYEE = "✅ Candidature notée"
CB_DEJA_ENVOYEE = "Déjà notée comme envoyée."
CB_GARDEE = "⏰ Offre gardée de côté."
CB_DEJA_GARDEE = "Déjà gardée de côté."
CB_IGNOREE = "🚫 Offre ignorée."
CB_DEJA_IGNOREE = "Déjà ignorée."
CB_ATTENTE = "⏳ Rédaction…"
CB_REDACTION_ABSENTE = "Rédaction non configurée."
CB_SANS_SCORE = "Offre non notée : brouillon impossible."
CB_RELANCE_DEJA = "Une seule relance par candidature : déjà faite."
CB_DEJA_DEPOSE = "Déjà déposé dans Gmail."
CB_DEPOSE = "📥 Brouillon Gmail créé"
CB_GMAIL_ABSENT = "Gmail non configuré : identifiants absents du .env."
CB_GMAIL_ECHEC = "Échec du dépôt Gmail : réessaie plus tard."
CB_LETTRES_ABSENT = "Dossier des lettres non configuré."
CB_FICHIERS_ECHEC = "Lettre impossible à générer : réessaie plus tard."
ECHEC_FICHIERS = "⚠️ La lettre n'a pas pu être écrite dans le dossier des lettres : rien n'a été enregistré."
ECHEC_OLLAMA = "⚠️ Ollama ne répond pas : lance-le puis réessaie."
ECHEC_REDACTION = "⚠️ La rédaction a échoué ou a dépassé le délai : réessaie."
CB_INTROUVABLE = "Offre introuvable."
CB_INCONNU = "Action inconnue."
CB_ENTREPRISE_IGNOREE = "❌ Entreprise ignorée."
CB_ENTREPRISE_INTROUVABLE = "Entreprise introuvable."


def cb_impossible(statut: str | None) -> str:
    return f"Impossible : l'offre est déjà « {statut or 'nouvelle'} »."


def message_accompagnement(poste: str | None, entreprise: str | None, nom: str) -> str:
    """Court message d'envoi, gabarit fixe : aucun appel au modèle, aucune invention.

    Sans poste, c'est une candidature spontanée.
    """
    chez = f" au sein de {entreprise}" if entreprise else ""
    objet = f"le poste de {poste}" if poste else "une candidature spontanée"
    return (
        "Madame, Monsieur,\n\n"
        f"Veuillez trouver ci-joint ma lettre de motivation pour {objet}{chez}.\n\n"
        "Je reste disponible pour un échange.\n\n"
        f"Cordialement,\n{nom}"
    )


def accompagnement_telegram(poste: str | None, entreprise: str | None, nom: str) -> str:
    entete = "✉️ <b>Message d'accompagnement</b>\n\n"
    return entete + escape(message_accompagnement(poste, entreprise, nom))[: LIMITE_TELEGRAM - len(entete)]


def echec_profil(message: str) -> str:
    return f"⚠️ {_e(message, 200)}"


def texte_brouillon(type_: str, texte: str) -> str:
    """Le brouillon à relire, échappé pour Telegram (HTML) et borné sous la limite."""
    titre = "Relance" if type_ == "relance" else "Brouillon d'e-mail"
    entete = f"✍️ <b>{titre}</b>\n\n"
    return entete + escape(texte)[: LIMITE_TELEGRAM - len(entete)]


def borner(lignes: list[str]) -> str:
    """Joint des lignes déjà échappées en s'arrêtant à une ligne entière sous la limite de Telegram."""
    sortie: list[str] = []
    taille = 0
    for ligne in lignes:
        taille += len(ligne) + 1
        if taille > LIMITE_TELEGRAM:
            break
        sortie.append(ligne)
    return "\n".join(sortie)


def liste_suivi(titre: str, lignes: list[tuple[Offre, Statut | None]]) -> str:
    corps = [
        f"• {_e(o.titre, 120)} · {_e(o.entreprise or 'entreprise non précisée', 60)}"
        + (f" · {s.value}" if s else "")
        for o, s in lignes
    ]
    return borner([f"<b>{titre}</b>", *corps])


def texte_stats(s: Stats) -> str:
    par = [f"• {_e(k, 30)} : {n}" for k, n in sorted(s.par_statut.items())] or ["• aucun suivi"]
    return borner(
        [
            "<b>Statistiques</b>",
            *par,
            f"Nouvelles sans suivi : {s.nouvelles}",
            f"Écartées par le filtre : {s.rejetees}",
        ]
    )


def texte_config(c: Config, pause: bool) -> str:
    return borner(
        [
            "<b>Réglages</b>",
            f"Rayon : {c.rayon_km:g} km · âge max : {c.age_max_jours} jours",
            f"Score minimum : {c.score_min} · alerte alternance dès {c.alerte_immediate_alternance_min}",
            f"Digest : {c.digest_max_offres} offres max, dès {c.heure_digest}",
            f"Alertes entre {c.plage_alertes[0]} et {c.plage_alertes[1]}",
            f"Envois : {'en pause' if pause else 'actifs'}",
        ]
    )


def rappel_j7(o: Offre) -> str:
    return "\n".join(
        [
            f"⏰ Il y a 7 jours, tu as postulé : <b>{_e(o.titre, 200)}</b>",
            f"🏢 {_e(o.entreprise or 'entreprise non précisée', 100)}",
            "Pense à relancer l'entreprise si tu n'as pas eu de réponse.",
            f'🔗 <a href="{escape(o.url)}">Voir l\'offre</a>',
        ]
    )


def cb_impossible_entreprise(statut: str | None) -> str:
    return f"Impossible : l'entreprise est déjà « {statut or 'nouvelle'} »."


def cb_plafond(maximum: int) -> str:
    return f"Plafond du jour atteint : {maximum} brouillons d'entreprise par jour."
