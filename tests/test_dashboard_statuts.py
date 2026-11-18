"""Le tableau de bord (web/) recopie les transitions du bot : les deux listes doivent rester identiques."""

import json
from pathlib import Path

from denicheur.db import repo
from denicheur.models import Statut

FICHIER = Path(__file__).resolve().parents[1] / "web" / "src" / "lib" / "transitions.json"
DONNEES = json.loads(FICHIER.read_text(encoding="utf-8"))


def _python() -> dict[str, set[str]]:
    return {
        (courant.value if courant else "nouvelle"): {s.value for s in permis}
        for courant, permis in repo._TRANSITIONS.items()
    }


def test_les_transitions_du_dashboard_sont_celles_du_bot():
    web = {courant: set(permis) for courant, permis in DONNEES["transitions"].items()}
    assert web == _python()


def test_le_dashboard_connait_chaque_statut_et_aucun_autre():
    assert set(DONNEES["libelles"]) == {s.value for s in Statut}
    assert all(libelle.strip() for libelle in DONNEES["libelles"].values())


def test_les_colonnes_du_tableau_couvrent_les_statuts_sauf_ignoree():
    assert set(DONNEES["colonnes"]) == {s.value for s in Statut} - {"ignoree"}
    assert len(DONNEES["colonnes"]) == len(set(DONNEES["colonnes"]))
