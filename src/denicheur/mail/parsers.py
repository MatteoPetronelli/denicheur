import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from email.message import EmailMessage, Message
from email.utils import parseaddr
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

log = logging.getLogger(__name__)

# Paramètres de suivi retirés des liens ; ceux qui identifient l'offre restent.
_SUIVI_PREFIXES = ("utm_", "trk", "tracking")
_SUIVI = {"refid", "trackingid", "tmtk", "alid", "plid"}


@dataclass(frozen=True)
class OffreMail:
    site: str
    titre: str
    entreprise: str
    ville: str
    departement: str
    lien: str
    texte: str
    # Identifiant stable quand le lien porte un jeton propre au destinataire.
    ident: str = ""


def lien_propre(url: str) -> str:
    p = urlsplit(url.strip())
    params = dict(parse_qsl(p.query))
    if p.netloc.endswith("indeed.com") and "jk" in params:  # jk = identifiant stable de l'offre
        return f"{p.scheme}://{p.netloc}/viewjob?jk={params['jk']}"
    garde = [
        (k, v)
        for k, v in parse_qsl(p.query)
        if not k.lower().startswith(_SUIVI_PREFIXES) and k.lower() not in _SUIVI
    ]
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(garde), ""))


_LIGNE_ENTREPRISE = re.compile(r"^(.+) - (.+?) \(([0-9]{2,3}|2[AB])\)$")
# Lignes d'un bloc Indeed qui ne décrivent pas le poste.
_BRUIT_INDEED = re.compile(r"^(Publié |il y a |Employeur réactif$|Candidature simplifiée$)", re.IGNORECASE)


def _indeed(msg: EmailMessage) -> list[OffreMail]:
    corps = msg.get_body(("plain",))
    if corps is None:
        return []
    offres = []
    # shortcut : seuls les blocs « Entreprise - Ville (dép) » sont lus (pas les offres en télétravail
    # sans ville) ; à étendre si une fixture réelle en montre.
    for bloc in re.split(r"\n\s*\n", corps.get_content()):
        lignes = [ligne.strip() for ligne in bloc.splitlines() if ligne.strip()]
        if len(lignes) < 3 or not lignes[-1].startswith("http"):
            continue
        m = _LIGNE_ENTREPRISE.match(lignes[1])
        if not m:
            continue
        texte = "\n".join(ligne for ligne in lignes[2:-1] if not _BRUIT_INDEED.match(ligne))
        offres.append(OffreMail("indeed", lignes[0], m[1], m[2], m[3], lien_propre(lignes[-1]), texte))
    return offres


# Jobtome : une offre par ligne « Titre (Entreprise - Ville): lien » ; ville parfois vide, pas de département.
_LIGNE_JOBTOME = re.compile(r"^(.+) \((.*) - (.*)\): (https://jobtomealert\.com/l/\S+)$")


def _jobtome(msg: EmailMessage) -> list[OffreMail]:
    corps = msg.get_body(("plain",))
    if corps is None:
        return []
    offres = []
    for ligne in corps.get_content().splitlines():
        m = _LIGNE_JOBTOME.match(ligne.strip())
        if m:
            # Le lien est une redirection avec jeton destinataire : gardé tel quel pour qu'il s'ouvre,
            # mais l'identité de l'offre ne dépend que du chemin.
            lien = m[4]
            offres.append(
                OffreMail("jobtome", m[1], m[2].strip(), m[3].strip(), "", lien, "", lien.split("?")[0])
            )
    return offres


# Domaine de l'expéditeur (suffixe) -> analyseur. Ajouter un site = une fonction + une fixture.
ANALYSEURS: dict[str, Callable[[EmailMessage], list[OffreMail]]] = {
    "indeed.com": _indeed,
    "jobtomealert.com": _jobtome,
}


def analyser(msg: Message) -> list[OffreMail]:
    domaine = parseaddr(str(msg["From"] or ""))[1].rpartition("@")[2].lower()
    for suffixe, analyseur in ANALYSEURS.items():
        if domaine == suffixe or domaine.endswith("." + suffixe):
            return analyseur(msg)  # type: ignore[arg-type]
    log.info("Expéditeur d'alerte non géré : %s", domaine or "inconnu")
    return []
