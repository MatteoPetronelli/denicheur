import email
import email.policy
import re
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path

import httpx

from denicheur.config import load_config
from denicheur.models import Piste
from denicheur.pipeline.dedupe import dedupliquer
from denicheur.sources.email_alertes import collecter, piste_du_titre

RACINE = Path(__file__).parent.parent
EMAILS = Path(__file__).parent / "fixtures" / "emails"
NOW = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)
CONFIG = load_config(RACINE / "config" / "recherches.yaml")


def _mails(*noms):
    def lire(since):
        lire.since = since
        return [
            email.message_from_binary_file((EMAILS / n).open("rb"), policy=email.policy.default) for n in noms
        ]

    return lire


def _http(appels: list[str], *, panne=False):
    def handler(request: httpx.Request) -> httpx.Response:
        appels.append(request.url.params["q"])
        if panne:
            raise httpx.ConnectError("réseau coupé")
        return httpx.Response(200, json={"features": [{"geometry": {"coordinates": [2.2, 48.9]}}]})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_pistes_par_mots_du_titre():
    assert piste_du_titre("Alternance développeur web") == Piste.ALTERNANCE
    assert piste_du_titre("Contrat d'apprentissage Python") == Piste.ALTERNANCE
    assert piste_du_titre("Alternant Ingénieur Master 2") == Piste.ALTERNANCE
    assert piste_du_titre("Développeur logiciel - Stage") == Piste.STAGE
    assert piste_du_titre("Stagiaire data") == Piste.STAGE
    assert piste_du_titre("Développeur full stack (H/F)") == Piste.AUTRE


def test_offres_normalisees():
    appels: list[str] = []
    offres = collecter(CONFIG, NOW, _mails("indeed_2.eml"), _http(appels))
    assert len(offres) == 5
    o = offres[0]
    assert o.source == "email:indeed"
    assert o.url.startswith("https://fr.indeed.com/viewjob?jk=")
    assert re.fullmatch(r"[0-9a-f]{40}", o.source_id)
    assert (o.piste, o.commune, o.entreprise) == (Piste.STAGE, "Issy-les-Moulineaux", "Capgemini")
    assert (o.lat, o.lon) == (48.9, 2.2)
    assert "Candidature simplifiée" not in o.description
    pistes = [x.piste for x in offres]
    assert pistes.count(Piste.ALTERNANCE) == 1  # « Alternant Ingénieur… » (Panachats)


def test_fenetre_glissante_de_sept_jours():
    lire = _mails("indeed_2.eml")
    collecter(CONFIG, NOW, lire, _http([]))
    assert lire.since == datetime(2026, 11, 9, 9, 0)  # UTC naïf, comme le reste du pipeline


def test_un_seul_appel_par_commune():
    appels: list[str] = []
    offres = collecter(CONFIG, NOW, _mails("indeed_1.eml"), _http(appels))
    communes = {(o.commune, o.lat) for o in offres}
    assert len(appels) == len(set(appels)) == len({o.commune for o in offres})
    assert len(communes) < len(offres)  # plusieurs offres à Nanterre, un appel


def test_geocodage_en_panne_coordonnees_vides():
    offres = collecter(CONFIG, NOW, _mails("indeed_2.eml"), _http([], panne=True))
    assert len(offres) == 5
    assert all(o.lat is None and o.lon is None for o in offres)


def test_meme_offre_dans_deux_mails_une_seule_apres_dedoublonnage():
    offres = collecter(CONFIG, NOW, _mails("indeed_1.eml", "indeed_3.eml"), _http([]))
    ids = [o.source_id for o in offres]
    assert len(ids) > len(set(ids))
    uniques = dedupliquer(offres, set(), set())
    # Liens sponsorisés (pagead) variables : la clé entreprise|titre|commune les fusionne.
    assert len(uniques) == len({(o.entreprise, o.titre, o.commune) for o in offres}) == 8


def test_sans_identifiants_aucune_lecture():
    assert collecter(CONFIG, NOW, None, _http([])) == []


def _mail_indeed(*blocs: str):
    msg = EmailMessage()
    msg["From"] = "Indeed <donotreply@jobalert.indeed.com>"
    msg.set_content(SEP.join(["Alerte Emploi Indeed", *blocs]))
    return msg


SEP = "\n\n"


def _bloc(titre: str, detail: str) -> str:
    return "\n".join(
        [
            titre,
            "ACME - Versailles (78)",
            detail,
            f"https://fr.indeed.com/rc/clk/dl?jk={len(titre)}{titre[-1]}",
        ]
    )


def test_teletravail_meme_partiel_detecte():
    msg = _mail_indeed(
        _bloc("Alternance dev A", "Télétravail partiel possible"),
        _bloc("Alternance dev B", "Poste hybride, 2 jours à distance"),
        _bloc("Alternance dev C", "Présentiel à Versailles"),
    )
    offres = collecter(CONFIG, NOW, lambda since: [msg], _http([]))
    assert [o.teletravail for o in offres] == [True, True, False]


def test_aucune_adresse_email_dans_les_descriptions():
    offres = collecter(CONFIG, NOW, _mails("indeed_1.eml", "indeed_2.eml", "indeed_3.eml"), _http([]))
    for o in offres:
        assert not re.search(r"[\w.+-]+@[\w-]+\.\w+", o.description)


def test_geocodage_reessaye_une_fois():
    essais = []

    def handler(request: httpx.Request) -> httpx.Response:
        essais.append(1)
        if len(essais) == 1:
            raise httpx.ReadTimeout("lent")
        return httpx.Response(200, json={"features": [{"geometry": {"coordinates": [2.2, 48.9]}}]})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    offres = collecter(CONFIG, NOW, _mails("indeed_3.eml"), http)
    assert offres[0].lat == 48.9
