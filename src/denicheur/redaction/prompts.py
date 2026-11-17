"""Prompts de rédaction : système stable (règles, modèle, profil), utilisateur propre à l'offre."""

from pathlib import Path

from denicheur.models import Offre, Piste, ScoreLLM
from denicheur.scoring.prompts import MAX_DESCRIPTION, _nettoyer

PROFILE = Path(__file__).resolve().parents[3] / "profile"
# Jamais cv_*.md : ils contiennent les coordonnées du candidat.
FICHIERS = ("regles_ecriture.md", "lettre_modele.md", "profil.md")
TYPES = ("email", "lettre", "relance", "spontanee")
LIGNE_PROFIL = "Éléments du profil utilisés"
# type -> (plage de mots, consigne)
PLAGES = {"email": (120, 180), "lettre": (250, 300), "relance": (120, 180), "spontanee": (120, 180)}
_CONSIGNES = {
    "email": "Rédige l'e-mail de candidature (corps du message seulement)",
    "lettre": "Rédige la lettre de motivation (corps de la lettre seulement)",
    "relance": "Rédige l'e-mail de relance d'une candidature envoyée il y a environ une semaine",
    "spontanee": (
        "Rédige une candidature spontanée (pas d'offre en cours) qui parle de l'activité de l'entreprise"
    ),
}
_DISPONIBILITE = {
    Piste.STAGE: "stage de 5 à 6 mois à partir de janvier 2027, février 2027 au plus tard",
    Piste.ALTERNANCE: (
        "alternance au rythme d'une semaine d'école pour deux semaines en entreprise, "
        "disponible dès que possible"
    ),
}


class ProfilManquant(Exception):
    """Un fichier de profil est absent : pas de brouillon sans règles ni profil."""


def message_systeme(dossier: Path = PROFILE) -> str:
    """Règles, modèle de lettre et profil dans cet ordre : octet-stable, ni date ni variable."""
    morceaux = []
    for nom in FICHIERS:
        try:
            morceaux.append((dossier / nom).read_text(encoding="utf-8").strip())
        except OSError:
            raise ProfilManquant(f"Fichier de profil introuvable : {nom}") from None
    return "\n\n---\n\n".join(morceaux)


def message_utilisateur(offre: Offre, score: ScoreLLM, type_: str) -> str:
    bas, haut = PLAGES[type_]
    description = _nettoyer(offre.description)[:MAX_DESCRIPTION]
    return (
        f"{_CONSIGNES[type_]}, de {bas} à {haut} mots "
        f"(vise {(bas + haut) // 2} mots, jamais moins de {bas}).\n"
        f"Poste : {_nettoyer(offre.titre)}\n"
        f"Entreprise : {offre.entreprise or 'non précisée'}\n"
        f"Lieu : {offre.commune or 'non précisé'}\n"
        f"Projet à citer : {score.projet_a_citer}\n"
        f"Disponibilité à indiquer : {_DISPONIBILITE[offre.piste]}\n"
        "Le texte doit être complet et prêt à envoyer : aucun texte entre crochets, aucun trou à compléter. "
        "Si l'offre ne donne aucun détail propre à l'entreprise, parle du poste et de ses missions tels que "
        "l'offre les décrit, sans rien inventer sur l'entreprise.\n"
        "Réponds uniquement par le texte demandé, sans phrase d'introduction ni commentaire.\n"
        f"Termine par une ligne « {LIGNE_PROFIL} : … ».\n"
        f"Description de l'offre :\n{description}"
    )
