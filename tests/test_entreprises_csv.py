from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from denicheur.db import repo
from denicheur.db.base import make_engine, migrer
from denicheur.db.tables import entreprises
from denicheur.entreprises.csv_import import importer_csv

NOW = datetime(2026, 11, 18, 9, tzinfo=UTC)
ENTETE = (
    "rang;entreprise;effectif;activite;naf;adresse;distance_km;candidature_spontanee_url;siret;"
    "statut;date_contact;notes"
)
REEL = Path(__file__).resolve().parents[1] / "entreprises_spontanees_mareil-marly.csv"


@pytest.fixture
def session(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    migrer(url)
    with Session(make_engine(url)) as s:
        yield s


def _csv(tmp_path, lignes):
    chemin = tmp_path / "e.csv"
    chemin.write_text("\n".join([ENTETE, *lignes]) + "\n", encoding="utf-8-sig")
    return chemin


L1 = "1;Société Été;10-19;Conseil en systèmes;62.02A;22 AVENUE X 78360 MONTESSON;4.7;https://lba/x;12345678900011;;;"
L2 = "2;BETA;0-0;Edition de logiciels;58.29C;1 rue Y 92500 RUEIL-MALMAISON;6,5;;98765432100022;;;"


def test_import_lit_le_bom_les_accents_et_les_champs(session, tmp_path):
    bilan = importer_csv(session, _csv(tmp_path, [L1, L2]), NOW)
    session.commit()
    assert (bilan.creees, bilan.mises_a_jour, bilan.ignorees) == (2, 0, 0)
    e = repo.lire_entreprise(session, 1)
    assert (e.nom, e.priorite, e.effectif, e.naf, e.origine) == ("Société Été", 1, "10-19", "62.02A", "csv")
    assert e.activite == "Conseil en systèmes"
    assert e.commune == "MONTESSON"
    assert e.distance_km == 4.7
    assert e.url_candidature == "https://lba/x"
    assert e.lat is None and e.lon is None


def test_distance_a_virgule_et_lien_absent(session, tmp_path):
    importer_csv(session, _csv(tmp_path, [L2]), NOW)
    e = repo.lire_entreprise(session, 1)
    assert e.distance_km == 6.5
    assert e.url_candidature is None


def test_lignes_invalides_ignorees_et_comptees(session, tmp_path):
    sans_siret = L1.replace("12345678900011", "")
    siret_court = L1.replace("12345678900011", "1234567890001")
    sans_nom = L1.replace("Société Été", "").replace("12345678900011", "11111111100011")
    bilan = importer_csv(session, _csv(tmp_path, [sans_siret, siret_court, sans_nom, L2]), NOW)
    assert (bilan.creees, bilan.ignorees) == (1, 3)
    assert repo.lire_entreprise(session, 1).siret == "98765432100022"


def test_reimport_met_a_jour_sans_dupliquer_ni_effacer_l_etat(session, tmp_path):
    chemin = _csv(tmp_path, [L1, L2])
    importer_csv(session, chemin, NOW)
    session.execute(
        update(entreprises).where(entreprises.c.id == 1).values(ignoree_le=datetime(2026, 11, 18))
    )
    session.commit()
    bilan = importer_csv(session, chemin, NOW)
    assert (bilan.creees, bilan.mises_a_jour) == (0, 2)
    assert session.execute(select(entreprises.c.id)).all() == [(1,), (2,)]
    assert session.execute(select(entreprises.c.ignoree_le).where(entreprises.c.id == 1)).scalar() is not None


def test_rang_illisible_donne_une_priorite_vide(session, tmp_path):
    importer_csv(session, _csv(tmp_path, [L1.replace("1;Société", "x;Société", 1)]), NOW)
    assert repo.lire_entreprise(session, 1).priorite is None


def test_fichier_absent_leve_oserror(session, tmp_path):
    with pytest.raises(OSError):
        importer_csv(session, tmp_path / "absent.csv", NOW)


def test_le_csv_du_projet_donne_150_entreprises_classees(session):
    bilan = importer_csv(session, REEL, NOW)
    session.commit()
    assert (bilan.creees, bilan.ignorees) == (150, 0)
    priorites = session.execute(select(entreprises.c.priorite).order_by(entreprises.c.id)).scalars().all()
    assert priorites == list(range(1, 151))


def test_colonnes_lat_et_lon_lues_avec_point_ou_virgule(session, tmp_path):
    chemin = tmp_path / "geo.csv"
    chemin.write_text(
        ENTETE + ";lat;lon\n" + L1 + ";48.912557;2.118516\n" + L2 + ";48,9;2,1\n", encoding="utf-8-sig"
    )
    importer_csv(session, chemin, NOW)
    assert (repo.lire_entreprise(session, 1).lat, repo.lire_entreprise(session, 1).lon) == (
        48.912557,
        2.118516,
    )
    assert (repo.lire_entreprise(session, 2).lat, repo.lire_entreprise(session, 2).lon) == (48.9, 2.1)


def test_lat_lon_illisibles_ou_vides_donnent_none(session, tmp_path):
    chemin = tmp_path / "geo.csv"
    chemin.write_text(ENTETE + ";lat;lon\n" + L1 + ";abc;\n", encoding="utf-8-sig")
    importer_csv(session, chemin, NOW)
    e = repo.lire_entreprise(session, 1)
    assert e.lat is None and e.lon is None


def test_le_csv_du_projet_porte_les_coordonnees_de_toutes_les_entreprises(session):
    importer_csv(session, REEL, NOW)
    lignes = session.execute(select(entreprises.c.lat, entreprises.c.lon)).all()
    assert len(lignes) == 150
    assert all(lat is not None and 48.5 < lat < 49.3 and 1.5 < lon < 2.8 for lat, lon in lignes)
