import email
import email.policy
import logging
import re
from pathlib import Path

import pytest

from denicheur.mail.parsers import analyser, lien_propre

EMAILS = Path(__file__).parent / "fixtures" / "emails"
ATTENDU = {
    "indeed_1.eml": 7,
    "indeed_2.eml": 5,
    "indeed_3.eml": 4,
    "jobtome_1.eml": 4,
    "jobtome_2.eml": 0,
    "linkedin_1.eml": 6,
}


def _charger(nom: str):
    with (EMAILS / nom).open("rb") as f:
        return email.message_from_binary_file(f, policy=email.policy.default)


@pytest.mark.parametrize(("nom", "n"), ATTENDU.items())
def test_nombre_d_offres_par_fixture(nom, n):
    assert len(analyser(_charger(nom))) == n


def test_champs_extraits_d_une_offre():
    o = analyser(_charger("indeed_1.eml"))[0]
    assert o.site == "indeed"
    assert o.titre == "Développeur full stack (H/F)"
    assert o.entreprise == "yele"
    assert o.ville == "Nanterre"
    assert o.departement == "92"
    assert o.lien == "https://fr.indeed.com/viewjob?jk=dfe83eea67d7d6af"
    assert "API REST" in o.texte
    assert "Publié" not in o.texte


def test_apostrophe_et_tiret_dans_la_ville():
    villes = {o.ville for o in analyser(_charger("indeed_1.eml"))}
    assert "L'Île-Saint-Denis" in villes


def test_expediteur_inconnu_zero_offre_et_journal(caplog):
    msg = _charger("indeed_1.eml")
    del msg["From"]
    msg["From"] = "Alertes <noreply@inconnu.example>"
    with caplog.at_level(logging.INFO):
        assert analyser(msg) == []
    assert "inconnu.example" in caplog.text


def test_pas_de_donnee_personnelle_dans_les_textes():
    for nom in ATTENDU:
        msg = _charger(nom)
        for o in analyser(msg):
            assert not re.search(r"[\w.+-]+@[\w-]+\.\w+", o.texte)
            assert "token=" not in o.texte
            assert "unsubscribe" not in o.texte.lower()
            assert "désabonner" not in o.texte.lower()


def test_meme_offre_deux_mails_meme_lien_propre():
    liens1 = {o.lien for o in analyser(_charger("indeed_1.eml"))}
    liens3 = {o.lien for o in analyser(_charger("indeed_3.eml"))}
    assert liens1 & liens3


@pytest.mark.parametrize(
    ("brut", "propre"),
    [
        (
            "https://fr.indeed.com/rc/clk/dl?jk=abc123&from=ja&qd=zzz&tk=1",
            "https://fr.indeed.com/viewjob?jk=abc123",
        ),
        ("https://x.fr/o/1?utm_source=a&id=7&trk=3&trackingId=9&refId=2#haut", "https://x.fr/o/1?id=7"),
        ("https://x.fr/o/1?id=7&tmtk=1&alid=2&plid=3", "https://x.fr/o/1?id=7"),
    ],
)
def test_lien_propre(brut, propre):
    assert lien_propre(brut) == propre


def test_jobtome_champs_et_identifiant_stable():
    offres = analyser(_charger("jobtome_1.eml"))
    o = offres[0]
    assert (o.site, o.entreprise, o.ville) == ("jobtome", "Ingeniance", "")
    assert o.titre == "Développeur Full Stack Java / Angular - Ia Augmentée - F/H"
    assert o.lien.startswith("https://jobtomealert.com/l/")
    assert (
        o.ident == o.lien.split("?")[0]
    )  # le chemin identifie l'offre, la requête porte le jeton du destinataire
    assert (offres[1].entreprise, offres[1].ville) == ("Quai des Notaires", "Paris")
    assert offres[2].titre == "Développeur Full Stack Java / React H/F (It) / Freelance"


def test_linkedin_champs_et_identifiant_stable():
    offres = analyser(_charger("linkedin_1.eml"))
    premiere = offres[0]
    assert premiere.site == "linkedin"
    assert premiere.titre == "Développeur fullstack PHP/Javascript - Alternance (H/F)"
    assert premiere.entreprise == "IKA"
    assert (premiere.ville, premiere.departement) == ("Boulogne-Billancourt", "")
    assert premiere.lien == "https://www.linkedin.com/jobs/view/4490941967"
    assert premiere.ident == "4490941967"
    assert [o.entreprise for o in offres] == [
        "IKA",
        "EDF",
        "KONCRETE",
        "Capgemini Engineering",
        "Thales",
        "Schneider Electric",
    ]


def test_linkedin_les_lignes_de_contexte_ne_decalent_pas_les_champs():
    # Lignes de contexte (« 2 anciens élèves », etc.) ou aucune : titre et entreprise restent les bons
    offres = {o.entreprise: o for o in analyser(_charger("linkedin_1.eml"))}
    assert offres["EDF"].titre == "STAGE - Développeur/euse Full Stack - Java /Angular F/H"
    assert offres["KONCRETE"].titre == "[Stage] Développeur Full Stack H/F"
    assert offres["Thales"].ville == "Cergy"


def test_linkedin_le_lien_perd_les_jetons_du_destinataire():
    for o in analyser(_charger("linkedin_1.eml")):
        assert re.fullmatch(r"https://www\.linkedin\.com/jobs/view/\d+", o.lien)


def test_linkedin_un_mail_sans_offre_donne_zero():
    msg = _charger("linkedin_1.eml")
    msg.set_content("Confirmez votre adresse e-mail : https://www.linkedin.com/comm/confirm")
    assert analyser(msg) == []


def test_linkedin_une_offre_sans_lieu_lisible_est_ignoree():
    msg = _charger("linkedin_1.eml")
    msg.set_content(
        "Titre seul\nEntreprise\nVoir l’offre d’emploi : https://www.linkedin.com/comm/jobs/view/123?x=1\n"
        "\n-----------------------------------------\n\n"
        "Entreprise\nParis, Île-de-France, France\nVoir l’offre d’emploi : https://www.linkedin.com/comm/jobs/view/456\n"
    )
    assert analyser(msg) == []
