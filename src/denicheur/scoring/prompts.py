import re
from datetime import date
from functools import cache
from pathlib import Path

from denicheur.models import Offre

PROFIL = Path(__file__).resolve().parents[3] / "profile" / "profil.md"
MAX_DESCRIPTION = 6000
_EMAIL = re.compile(r"\S+@\S+")
_TEL = re.compile(r"\b0\d([\s.-]?\d{2}){4}\b")
_DIPLOMES = {"3": "Bac+0", "4": "Bac", "5": "Bac+2", "6": "Bac+3", "7": "Bac+5", "8": "Bac+8"}

# Octet-stable : ni date, ni identifiant (cache KV d'Ollama). La date du jour est dans le message utilisateur.
_SYSTEME = """\
Tu es un assistant qui évalue des offres de stage et d'alternance en informatique pour un seul candidat.
Tu réponds uniquement par un JSON conforme au schéma demandé, en français. N'invente rien : si une \
information manque dans l'offre, reste neutre et ne la suppose pas.

## Profil du candidat
{profil}

## Barème (100 points)
- Adéquation des compétences (React, TypeScript, Python, IA, SQL) : 40
- Type, durée et calendrier : 20
- Localisation et distance : 15
- Niveau demandé par rapport à un Bac+3 : 15
- Intérêt du poste (IA, produit, autonomie, apprentissage) : 10

## Règles par piste
- Stage : durée de 5 à 6 mois, début en janvier ou février. Durée ou date absentes : neutre. Durée hors \
5-6 mois : malus et mention dans les points faibles.
- Alternance : durée de 1 à 2 ans. Démarrage immédiat ou très proche : bonus (le candidat est déjà inscrit \
à l'école, seul le contrat en entreprise manque). Début dans plus de 6 mois : malus. Rythme annoncé \
différent d'une semaine d'école pour deux semaines en entreprise : renseigne le champ alerte, sans \
éliminer l'offre.
- Le candidat prépare un Bac+3. Le diplôme indiqué est le plus haut niveau accepté, pas le minimum : si \
les conditions d'accès donnent une fourchette qui inclut Bac+3 ou moins (par exemple « Bac+2 à Bac+5 »), \
ou si rien n'impose Bac+5, n'applique aucun malus ni alerte sur le niveau. Seule une offre qui exige \
clairement Bac+5 minimum reçoit un malus et une alerte sur le niveau, sans être éliminée.
- L'école exige du présentiel. Si la description évoque du télétravail, du remote ou de l'hybride, applique \
un malus de localisation et renseigne le champ alerte.
- Si le lieu est marqué « lieu à vérifier », ou si la description situe le poste dans une autre ville que \
le lieu indiqué, applique un fort malus de localisation et renseigne le champ alerte avec la ville citée.
- Bonus léger si l'offre valorise l'usage d'outils d'IA pour développer (Claude Code, Cursor, Copilot).

## Plafonds impératifs
Applique ces plafonds avant de donner le score ; ils priment sur le barème. Utilise toute l'échelle
de 0 à 100 et ne donne jamais une note moyenne par défaut.
- Le poste n'est pas du développement logiciel (RH, paie, conseil en stratégie ou en management,
  transformation, consultant fonctionnel, analyse métier, sujets de stage de cabinet) : 20 au maximum.
- L'offre vise un profil confirmé ou senior : 30 au maximum.
- Lieu à vérifier, ou autre ville citée dans la description : 40 au maximum.
- Distance supérieure à 40 km du centre : 45 au maximum.
- Mission de développement (web, logiciel, sécurité) proche du candidat et à moins de 30 km :
  entre 60 et 85 selon les technologies et le calendrier.
- Au-dessus de 85 : seulement un poste de développement qui cite React, TypeScript, Python ou l'IA,
  proche et disponible rapidement.

## Sortie
- score : entier de 0 à 100.
- type : stage, alternance ou autre.
- points_forts et points_faibles : 3 éléments au plus chacun, courts.
- alerte : une phrase si un point mérite l'attention du candidat, sinon null.
- projet_a_citer : un seul projet pris dans la liste des projets du profil, le plus pertinent pour l'offre.
- resume : deux phrases en français.
"""


@cache
def system_scoring() -> str:
    return _SYSTEME.format(profil=PROFIL.read_text(encoding="utf-8").strip())


def _nettoyer(texte: str) -> str:
    """Retire e-mails et téléphones du texte d'offre : aucune donnée de contact vers le LLM."""
    return _TEL.sub("[contact]", _EMAIL.sub("[contact]", texte))


def user_message(o: Offre, today: date) -> str:
    lieu = o.commune or "inconnue"
    if o.distance_km is not None:
        lieu += f" ({o.distance_km:.0f} km du centre)"
    if o.lieu_a_verifier:
        lieu += ", lieu à vérifier"
    if o.debut_des_que_possible:
        debut = "dès que possible"
    else:
        debut = o.debut.isoformat() if o.debut else "non précisé"
    diplome = _DIPLOMES.get(o.niveau_diplome or "", "non précisé")
    duree = f"{o.duree_mois} mois" if o.duree_mois else "non précisée"
    return (
        f"Date du jour : {today.isoformat()}\n"
        f"Titre : {_nettoyer(o.titre)}\n"
        f"Entreprise : {o.entreprise or 'non précisée'}\n"
        f"Lieu : {lieu}\n"
        f"Piste : {o.piste.value}\n"
        f"Durée : {duree}\n"
        f"Début : {debut}\n"
        f"Diplôme (niveau maximal accepté, pas une exigence) : {diplome}\n"
        f"Description :\n{_nettoyer(o.description)[:MAX_DESCRIPTION]}"
    )
