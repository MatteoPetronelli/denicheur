"""Tout le texte vu par l'utilisateur (Telegram) vit ici."""

from html import escape

from denicheur.models import Offre, ScoreLLM

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


def echec_collecte(type_erreur: str) -> str:
    return f"⚠️ La collecte du jour a échoué : {type_erreur}"
