import hashlib

from denicheur.models import Offre
from denicheur.pipeline.normalize import normaliser_texte as norm


def cle_dedup(o: Offre) -> str:
    return hashlib.sha256(f"{norm(o.entreprise)}|{norm(o.titre)}|{norm(o.commune)}".encode()).hexdigest()


def dedupliquer(offres: list[Offre], deja_vues_urls: set[str], deja_vues_cles: set[str]) -> list[Offre]:
    """Garde la première offre de chaque URL / clé, hors celles déjà connues."""
    urls, cles = set(deja_vues_urls), set(deja_vues_cles)
    gardees = []
    for o in offres:
        cle = cle_dedup(o)
        if o.url in urls or cle in cles:
            continue
        urls.add(o.url)
        cles.add(cle)
        gardees.append(o)
    return gardees
