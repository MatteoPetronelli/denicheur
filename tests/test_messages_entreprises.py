import pytest

from denicheur.messages_fr import LIMITE_TELEGRAM, entete_entreprises, format_entreprise
from denicheur.models import Entreprise


def _e(**kw):
    base = {
        "siret": "12345678900011", "nom": "SKAIZEN GROUP", "activite": "Conseil en systèmes et logiciels",
        "effectif": "10-19", "commune": "MONTESSON", "distance_km": 4.7,
        "url_candidature": "https://labonnealternance.apprentissage.beta.gouv.fr/x", "origine": "csv",
    }  # fmt: skip
    return Entreprise(**{**base, **kw})


COMPLET = "\n".join(
    [
        "🏢 <b>SKAIZEN GROUP</b>",
        "💼 Conseil en systèmes et logiciels · 10-19 salariés",
        "📍 MONTESSON (5 km)",
        '🔗 <a href="https://labonnealternance.apprentissage.beta.gouv.fr/x">Candidature spontanée</a>',
    ]
)


def test_message_complet():
    assert format_entreprise(_e(), []) == COMPLET


def test_offres_ouvertes_ajoutees_une_ligne_chacune():
    m = format_entreprise(_e(), ["Alternance dev web", "Stage data"])
    assert m == COMPLET + "\n📌 Offre ouverte aussi : Alternance dev web\n📌 Offre ouverte aussi : Stage data"


def test_champs_absents_omis_sans_ligne_vide():
    m = format_entreprise(
        _e(activite=None, effectif=None, commune=None, distance_km=None, url_candidature=None), []
    )
    assert m == "🏢 <b>SKAIZEN GROUP</b>"


def test_effectif_seul_ou_activite_seule():
    assert "💼 10-19 salariés" in format_entreprise(_e(activite=None), [])
    assert "💼 Conseil en systèmes et logiciels\n" in format_entreprise(_e(effectif=None), []) + "\n"


def test_commune_sans_distance_et_distance_sans_commune():
    assert "📍 MONTESSON\n" in format_entreprise(_e(distance_km=None), []) + "\n"
    assert "📍 5 km" in format_entreprise(_e(commune=None), [])


def test_html_echappe_dans_le_nom_l_activite_la_commune_et_les_offres():
    m = format_entreprise(
        _e(nom="<script>A&B</script>", activite="<i>x</i>", commune="<b>Y</b>"), ['<a href="x">piège</a>']
    )
    assert "<script>" not in m and "<i>" not in m and "<b>Y" not in m and '<a href="x">' not in m
    assert "&lt;script&gt;A&amp;B&lt;/script&gt;" in m
    assert "&lt;a href=&quot;x&quot;&gt;piège&lt;/a&gt;" in m


@pytest.mark.parametrize("url", ["javascript:alert(1)", "ftp://x", "//x", "", "https:/x"])
def test_lien_non_http_jamais_affiche(url):
    m = format_entreprise(_e(url_candidature=url), [])
    assert "🔗" not in m and "<a " not in m


def test_lien_avec_guillemet_ne_sort_pas_de_l_attribut():
    m = format_entreprise(_e(url_candidature='https://x/"onmouseover="y'), [])
    assert '"onmouseover' not in m and "&quot;" in m


def test_message_borne_meme_avec_des_champs_enormes():
    enorme = "x" * 5000
    m = format_entreprise(_e(nom=enorme, activite=enorme, commune=enorme), [enorme] * 3)
    assert len(m) < LIMITE_TELEGRAM


def test_entete_au_singulier_et_au_pluriel():
    assert entete_entreprises(1) == "🏢 1 entreprise à démarcher aujourd'hui"
    assert entete_entreprises(10) == "🏢 10 entreprises à démarcher aujourd'hui"


def test_au_plus_trois_offres_ouvertes_affichees():
    m = format_entreprise(_e(), [f"Offre {n}" for n in range(1, 6)])
    assert m.count("📌 Offre ouverte aussi :") == 3 and "Offre 3" in m and "Offre 4" not in m
