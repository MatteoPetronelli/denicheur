"""Ce à quoi une candidature s'adresse : une offre (avec un poste) ou une entreprise seule."""

from dataclasses import dataclass

from denicheur.models import Entreprise, Offre


@dataclass(frozen=True)
class Cible:
    entreprise: str | None
    poste: str | None = None  # None : candidature spontanée

    @classmethod
    def depuis_offre(cls, offre: Offre) -> "Cible":
        return cls(offre.entreprise, offre.titre)

    @classmethod
    def depuis_entreprise(cls, entreprise: Entreprise) -> "Cible":
        return cls(entreprise.nom)


def en_cible(x: "Offre | Cible") -> Cible:
    return x if isinstance(x, Cible) else Cible.depuis_offre(x)
