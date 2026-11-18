import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from denicheur.db.base import RACINE, make_engine, migrer

MAINTENANT = "2026-11-18 09:00:00"


@pytest.fixture
def url(tmp_path):
    return f"sqlite:///{tmp_path / 'test.db'}"


def _entreprise(c, siret="12345678900011", **kw):
    valeurs = {"siret": siret, "nom": "ACME", "origine": "csv", "cree_le": MAINTENANT, "maj_le": MAINTENANT}
    valeurs.update(kw)
    colonnes = ", ".join(valeurs)
    parametres = ", ".join(f":{k}" for k in valeurs)
    c.execute(text(f"insert into entreprises ({colonnes}) values ({parametres})"), valeurs)


def _suivi(c, entreprise_id):
    c.execute(
        text(
            "insert into candidatures (entreprise_id, statut, cree_le, maj_le) "
            "values (:e, 'interessante', :t, :t)"
        ),
        {"e": entreprise_id, "t": MAINTENANT},
    )


def test_base_neuve_a_sept_tables(url):
    migrer(url)
    noms = set(inspect(make_engine(url)).get_table_names())
    assert {
        "offres",
        "scores",
        "candidatures",
        "brouillons",
        "executions",
        "parametres",
        "entreprises",
    } <= noms


def test_colonnes_de_la_table_entreprises(url):
    migrer(url)
    colonnes = {c["name"] for c in inspect(make_engine(url)).get_columns("entreprises")}
    attendu = {
        "id", "siret", "nom", "activite", "naf", "effectif", "adresse", "commune", "lat", "lon",
        "distance_km", "priorite", "url_candidature", "origine", "listee_le", "contactee_le",
        "ignoree_le", "cree_le", "maj_le",
    }  # fmt: skip
    assert colonnes == attendu


def test_offre_porte_un_siret_facultatif(url):
    migrer(url)
    colonnes = {c["name"]: c for c in inspect(make_engine(url)).get_columns("offres")}
    assert colonnes["siret"]["nullable"] is True


def test_cle_etrangere_du_suivi_vers_les_entreprises(url):
    migrer(url)
    cles = inspect(make_engine(url)).get_foreign_keys("candidatures")
    assert any(
        k["constrained_columns"] == ["entreprise_id"] and k["referred_table"] == "entreprises" for k in cles
    )


def test_siret_unique(url):
    migrer(url)
    with make_engine(url).begin() as c:
        _entreprise(c)
    with pytest.raises(IntegrityError), make_engine(url).begin() as c:
        _entreprise(c, nom="Autre")


def test_un_seul_suivi_par_entreprise(url):
    migrer(url)
    with make_engine(url).begin() as c:
        _entreprise(c)
        _suivi(c, 1)
    with pytest.raises(IntegrityError), make_engine(url).begin() as c:
        _suivi(c, 1)


def test_plusieurs_suivis_d_offres_sans_entreprise(url):
    migrer(url)
    with make_engine(url).begin() as c:
        for _ in range(2):
            c.execute(
                text("insert into candidatures (statut, cree_le, maj_le) values ('interessante', :t, :t)"),
                {"t": MAINTENANT},
            )
        assert c.execute(text("select count(*) from candidatures")).scalar() == 2


def test_montee_de_version_conserve_les_lignes(url):
    migrer(url, "0001")
    with make_engine(url).begin() as c:
        c.execute(
            text(
                "insert into offres (source, source_id, url, cle_dedup, titre, piste, description, vue_le, "
                "lieu_a_verifier, debut_des_que_possible) "
                "values ('lba', '1', 'https://x/1', 'k', 'Dev', 'alternance', 'd', :t, 0, 0)"
            ),
            {"t": MAINTENANT},
        )
        c.execute(
            text(
                "insert into candidatures (offre_id, statut, cree_le, maj_le) "
                "values (1, 'interessante', :t, :t)"
            ),
            {"t": MAINTENANT},
        )
        c.execute(
            text(
                "insert into brouillons (candidature_id, type, contenu, gmail_draft, cree_le) "
                "values (1, 'email', 'texte', 0, :t)"
            ),
            {"t": MAINTENANT},
        )
    migrer(url)
    with make_engine(url).connect() as c:
        assert c.execute(text("select count(*) from offres")).scalar() == 1
        assert c.execute(text("select offre_id, statut from candidatures")).one() == (1, "interessante")
        assert c.execute(text("select candidature_id, contenu from brouillons")).one() == (1, "texte")
        assert c.execute(text("select siret from offres")).scalar() is None


def test_deuxieme_migration_sans_effet(url):
    migrer(url)
    with make_engine(url).begin() as c:
        _entreprise(c)
    migrer(url)
    with make_engine(url).connect() as c:
        assert c.execute(text("select count(*) from entreprises")).scalar() == 1


def test_retour_arriere_conserve_les_offres(url):
    migrer(url)
    with make_engine(url).begin() as c:
        c.execute(
            text(
                "insert into offres (source, source_id, url, cle_dedup, titre, piste, description, vue_le, "
                "lieu_a_verifier, debut_des_que_possible, siret) "
                "values ('lba', '1', 'https://x/1', 'k', 'Dev', 'alternance', 'd', :t, 0, 0, "
                "'12345678900011')"
            ),
            {"t": MAINTENANT},
        )
    cfg = AlembicConfig(str(RACINE / "alembic.ini"))
    cfg.set_main_option("script_location", str(RACINE / "migrations"))
    cfg.attributes["url"] = url
    command.downgrade(cfg, "0001")
    noms = set(inspect(make_engine(url)).get_table_names())
    assert "entreprises" not in noms
    with make_engine(url).connect() as c:
        assert c.execute(text("select count(*) from offres")).scalar() == 1
