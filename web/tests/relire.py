"""Relit avec le code Python une ligne écrite par le dashboard : même format de date, même statut."""

import json
import sys
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from denicheur.db import repo
from denicheur.db.base import make_engine
from denicheur.db.tables import candidatures, entreprises


def _iso(valeur: datetime | None) -> str | None:
    return valeur.isoformat() if valeur else None


chemin, genre, ident = sys.argv[1], sys.argv[2], int(sys.argv[3])
with Session(make_engine(f"sqlite:///{chemin}")) as session:
    if genre == "offre":
        statut = repo.statut_de(session, ident)
        cible = candidatures.c.offre_id == ident
    else:
        statut = repo.statut_de_entreprise(session, ident)
        cible = candidatures.c.entreprise_id == ident
    ligne = session.execute(select(candidatures).where(cible)).mappings().one_or_none()
    sortie = {"statut": statut.value if statut else None}
    if ligne:
        sortie |= {k: _iso(ligne[k]) for k in ("envoyee_le", "cree_le", "maj_le")}
    if genre == "entreprise":
        e = session.execute(select(entreprises).where(entreprises.c.id == ident)).mappings().one()
        sortie |= {k: _iso(e[k]) for k in ("contactee_le", "ignoree_le")}
    print(json.dumps(sortie))
