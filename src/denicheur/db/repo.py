"""Toutes les écritures/lectures SQL passent ici (pas de session brute dans le pipeline)."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from denicheur.db.tables import (
    brouillons,
    candidatures,
    entreprises,
    executions,
    offres,
    parametres,
    scores,
)
from denicheur.models import Entreprise, Offre, Piste, ScoreLLM, Statut

PARIS = ZoneInfo("Europe/Paris")
# Champs de `Offre` stockés tels quels dans `offres`.
_NON_PERSISTES = {"teletravail"}
_CHAMPS_OFFRE = [c for c in Offre.model_fields if c not in _NON_PERSISTES]


def _utc_naif(dt: datetime) -> datetime:
    """SQLite ne garde pas le fuseau : on stocke l'UTC sans tzinfo."""
    return dt.astimezone(UTC).replace(tzinfo=None) if dt.tzinfo else dt


def inserer_offre(session: Session, offre: Offre, *, cle_dedup: str, now: datetime) -> int:
    """Insère l'offre ; si (source, source_id) ou url existe déjà, retourne l'id existant."""
    valeurs = offre.model_dump(exclude=_NON_PERSISTES)
    valeurs["piste"] = offre.piste.value
    for champ in ("publiee_le", "expire_le"):
        if valeurs[champ] is not None:
            valeurs[champ] = _utc_naif(valeurs[champ])
    valeurs.update(cle_dedup=cle_dedup, vue_le=_utc_naif(now))
    # shortcut: upsert SQLite-only ; passer à une lecture-puis-insertion si PostgreSQL est un jour utilisé.
    session.execute(sqlite_insert(offres).values(**valeurs).on_conflict_do_nothing())
    return session.execute(
        select(offres.c.id).where(
            (offres.c.url == offre.url)
            | ((offres.c.source == offre.source) & (offres.c.source_id == offre.source_id))
        )
    ).scalar_one()


def lire_offre(session: Session, offre_id: int) -> Offre:
    ligne = session.execute(select(offres).where(offres.c.id == offre_id)).mappings().one()
    valeurs = {k: ligne[k] for k in _CHAMPS_OFFRE}
    for champ in ("publiee_le", "expire_le"):
        if valeurs[champ] is not None:
            valeurs[champ] = valeurs[champ].replace(tzinfo=UTC)
    return Offre(**valeurs)


def inserer_score(
    session: Session, offre_id: int, score: ScoreLLM, *, modele: str, prompt_tokens: int,
    output_tokens: int, duree_s: float, now: datetime,
) -> None:  # fmt: skip
    session.execute(
        scores.insert().values(
            offre_id=offre_id, piste=score.type, score=score.score, points_forts=score.points_forts,
            points_faibles=score.points_faibles, alerte=score.alerte, projet_a_citer=score.projet_a_citer,
            resume=score.resume, modele=modele, prompt_tokens=prompt_tokens, output_tokens=output_tokens,
            duree_s=duree_s, cree_le=_utc_naif(now),
        )
    )  # fmt: skip


def lire_score(session: Session, offre_id: int) -> ScoreLLM | None:
    ligne = session.execute(select(scores).where(scores.c.offre_id == offre_id)).mappings().one_or_none()
    if ligne is None:
        return None
    return ScoreLLM(
        score=ligne["score"], type=ligne["piste"], points_forts=ligne["points_forts"],
        points_faibles=ligne["points_faibles"], alerte=ligne["alerte"],
        projet_a_citer=ligne["projet_a_citer"], resume=ligne["resume"],
    )  # fmt: skip


def offres_a_notifier(session: Session, score_min: int, limite: int) -> list[tuple[int, Offre, ScoreLLM]]:
    """Offres retenues, notées ≥ `score_min`, pas encore notifiées, meilleur score d'abord."""
    ids = session.execute(
        select(offres.c.id)
        .join(scores, scores.c.offre_id == offres.c.id)
        .where(offres.c.notifiee_le.is_(None), offres.c.motif_rejet.is_(None), scores.c.score >= score_min)
        .order_by(scores.c.score.desc(), offres.c.id)
        .limit(limite)
    ).scalars()  # fmt: skip
    return [(i, lire_offre(session, i), s) for i in list(ids) if (s := lire_score(session, i))]


def offres_sans_score(session: Session) -> list[tuple[int, Offre]]:
    """Offres retenues pas encore notées (y compris celles dont le scoring a échoué)."""
    ids = session.execute(
        select(offres.c.id)
        .outerjoin(scores, scores.c.offre_id == offres.c.id)
        .where(offres.c.motif_rejet.is_(None), scores.c.offre_id.is_(None))
        # Alternance d'abord (alerte instantanée), puis les plus récentes : un gros lot de stages
        # ne retarde pas les alternances, et le plafond d'appels du jour ne frappe que les plus vieilles.
        .order_by(
            case((offres.c.piste == "alternance", 0), else_=1),
            offres.c.publiee_le.desc(),  # SQLite place les dates absentes en dernier
            offres.c.id,
        )
    ).scalars()  # fmt: skip
    return [(i, lire_offre(session, i)) for i in list(ids)]


def ouvrir_execution(session: Session, mode: str, now: datetime) -> int:
    res = session.execute(executions.insert().values(debut=_utc_naif(now), mode=mode, erreurs=[]))
    return int(res.inserted_primary_key[0])  # type: ignore[attr-defined]


def clore_execution(session: Session, execution_id: int, now: datetime, **champs: object) -> None:
    session.execute(
        executions.update().where(executions.c.id == execution_id).values(fin=_utc_naif(now), **champs)
    )


def marquer_notifiee(session: Session, offre_id: int, now: datetime) -> None:
    session.execute(offres.update().where(offres.c.id == offre_id).values(notifiee_le=_utc_naif(now)))


def urls_connues(session: Session) -> set[str]:
    return set(session.execute(select(offres.c.url)).scalars())


def cles_connues(session: Session) -> set[str]:
    return set(session.execute(select(offres.c.cle_dedup)).scalars())


def appels_llm_aujourdhui(session: Session, now: datetime) -> int:
    """Scores créés pendant le jour calendaire Europe/Paris de `now`."""
    jour = now.astimezone(PARIS).date()
    debut = datetime.combine(jour, time.min, tzinfo=PARIS)
    fin = datetime.combine(jour, time.max, tzinfo=PARIS)
    return session.execute(
        select(func.count()).select_from(scores).where(
            scores.c.cree_le.between(_utc_naif(debut), _utc_naif(fin))
        )
    ).scalar_one()  # fmt: skip


def get_param(session: Session, cle: str) -> str | None:
    return session.execute(select(parametres.c.valeur).where(parametres.c.cle == cle)).scalar_one_or_none()


def set_param(session: Session, cle: str, valeur: str) -> None:
    stmt = sqlite_insert(parametres).values(cle=cle, valeur=valeur)
    session.execute(stmt.on_conflict_do_update(index_elements=["cle"], set_={"valeur": valeur}))


class OffreInconnue(Exception):
    pass


class TransitionInvalide(Exception):
    pass


_ISSUES = (Statut.ENTRETIEN, Statut.REFUS, Statut.OFFRE, Statut.SANS_REPONSE)
# Statut courant (None = nouvelle, sans ligne) -> statuts atteignables ; « ignoree » l'est depuis partout.
_TRANSITIONS: dict[Statut | None, frozenset[Statut]] = {
    None: frozenset({Statut.INTERESSANTE, Statut.CANDIDATURE_ENVOYEE, Statut.IGNOREE}),
    Statut.INTERESSANTE: frozenset({Statut.CANDIDATURE_ENVOYEE, Statut.IGNOREE}),
    Statut.CANDIDATURE_ENVOYEE: frozenset({Statut.RELANCEE, *_ISSUES, Statut.IGNOREE}),
    Statut.RELANCEE: frozenset({*_ISSUES, Statut.IGNOREE}),
    **{s: frozenset({Statut.IGNOREE}) for s in _ISSUES},
}
_TRANSITIONS[Statut.IGNOREE] = frozenset()


def statut_de(session: Session, offre_id: int) -> Statut | None:
    brut = session.execute(
        select(candidatures.c.statut).where(candidatures.c.offre_id == offre_id)
    ).scalar_one_or_none()
    return Statut(brut) if brut else None


def marquer(session: Session, offre_id: int, statut: Statut, now: datetime) -> None:
    """Fait avancer le suivi d'une offre ; une seule ligne par offre, créée au premier marquage."""
    if session.execute(select(offres.c.id).where(offres.c.id == offre_id)).first() is None:
        raise OffreInconnue(offre_id)
    courant = statut_de(session, offre_id)
    if courant == statut:
        return
    if statut not in _TRANSITIONS[courant]:
        raise TransitionInvalide(f"{courant or 'nouvelle'} -> {statut}")
    maintenant = _utc_naif(now)
    envoi = {"envoyee_le": maintenant} if statut is Statut.CANDIDATURE_ENVOYEE else {}
    if (
        courant is None
    ):  # shortcut: pas d'index unique sur offre_id (il faudrait Alembic) ; un seul écrivain à la fois
        session.execute(
            candidatures.insert().values(
                offre_id=offre_id, statut=statut.value, cree_le=maintenant, maj_le=maintenant, **envoi
            )
        )
    else:
        session.execute(
            candidatures.update()
            .where(candidatures.c.offre_id == offre_id)
            .values(statut=statut.value, maj_le=maintenant, **envoi)
        )


def marquer_rappelee(session: Session, offre_id: int, now: datetime) -> None:
    session.execute(
        candidatures.update().where(candidatures.c.offre_id == offre_id).values(rappel_le=_utc_naif(now))
    )


def candidatures_a_relancer(session: Session, today: date) -> list[tuple[int, Offre]]:
    """Candidatures envoyées depuis au moins 7 jours (date Paris) et jamais rappelées."""
    lignes = session.execute(
        select(candidatures.c.offre_id, candidatures.c.envoyee_le)
        .where(candidatures.c.statut == Statut.CANDIDATURE_ENVOYEE.value, candidatures.c.rappel_le.is_(None))
        .order_by(candidatures.c.envoyee_le)
    ).all()
    limite = today - timedelta(days=7)
    return [
        (oid, lire_offre(session, oid))
        for oid, envoyee in lignes
        if envoyee.replace(tzinfo=UTC).astimezone(PARIS).date() <= limite
    ]


@dataclass
class Stats:
    par_statut: dict[str, int]
    nouvelles: int  # notifiées, sans suivi
    rejetees: int  # écartées par le préfiltre


def stats(session: Session) -> Stats:
    par_statut: dict[str, int] = dict(
        session.execute(select(candidatures.c.statut, func.count()).group_by(candidatures.c.statut)).all()
    )
    suivies = select(candidatures.c.offre_id)
    nouvelles = session.execute(
        select(func.count())
        .select_from(offres)
        .where(offres.c.notifiee_le.is_not(None), offres.c.id.not_in(suivies))
    ).scalar_one()
    rejetees = session.execute(
        select(func.count()).select_from(offres).where(offres.c.motif_rejet.is_not(None))
    ).scalar_one()
    return Stats(par_statut, nouvelles, rejetees)


def _avec_score(session: Session, ids: list[int]) -> list[tuple[int, Offre, ScoreLLM]]:
    return [(i, lire_offre(session, i), s) for i in ids if (s := lire_score(session, i))]


def offres_du_jour(session: Session, jour: date) -> list[tuple[int, Offre, ScoreLLM]]:
    """Offres notifiées pendant le jour Paris `jour`, sans suivi, meilleur score d'abord."""
    debut = datetime.combine(jour, time.min, tzinfo=PARIS)
    ids = session.execute(
        select(offres.c.id)
        .join(scores, scores.c.offre_id == offres.c.id)
        .where(
            offres.c.notifiee_le >= _utc_naif(debut),
            offres.c.notifiee_le < _utc_naif(debut + timedelta(days=1)),
            offres.c.id.not_in(select(candidatures.c.offre_id)),
        )
        .order_by(scores.c.score.desc(), offres.c.id)
    ).scalars()  # fmt: skip
    return _avec_score(session, list(ids))


def meilleures_offres(session: Session, piste: Piste, limite: int) -> list[tuple[int, Offre, ScoreLLM]]:
    """Meilleures offres notées d'une piste, retenues par le préfiltre et non écartées."""
    ecartees = select(candidatures.c.offre_id).where(candidatures.c.statut == Statut.IGNOREE.value)
    ids = session.execute(
        select(offres.c.id)
        .join(scores, scores.c.offre_id == offres.c.id)
        .where(offres.c.piste == piste.value, offres.c.motif_rejet.is_(None), offres.c.id.not_in(ecartees))
        .order_by(scores.c.score.desc(), offres.c.id)
        .limit(limite)
    ).scalars()  # fmt: skip
    return _avec_score(session, list(ids))


def suivi_en_cours(session: Session, limite: int) -> list[tuple[int, Offre, Statut]]:
    """Candidatures suivies et non écartées, la plus récemment modifiée d'abord."""
    lignes = session.execute(
        select(candidatures.c.offre_id, candidatures.c.statut)
        .where(candidatures.c.statut != Statut.IGNOREE.value)
        .order_by(candidatures.c.maj_le.desc(), candidatures.c.id.desc())
        .limit(limite)
    ).all()
    return [(oid, lire_offre(session, oid), Statut(statut)) for oid, statut in lignes]


class RelanceDejaFaite(Exception):
    pass


@dataclass
class BrouillonLu:
    id: int
    offre_id: int
    type: str
    contenu: str
    depose: bool  # déjà dans les brouillons Gmail


def _nb_relances(session: Session, offre_id: int) -> int:
    return session.execute(
        select(func.count())
        .select_from(brouillons.join(candidatures, brouillons.c.candidature_id == candidatures.c.id))
        .where(candidatures.c.offre_id == offre_id, brouillons.c.type == "relance")
    ).scalar_one()


def verifier_brouillon(session: Session, offre_id: int, type_: str) -> None:
    """Lève si un brouillon de ce type n'est pas permis ; à appeler avant de payer un appel au modèle."""
    if session.execute(select(offres.c.id).where(offres.c.id == offre_id)).first() is None:
        raise OffreInconnue(offre_id)
    courant = statut_de(session, offre_id)
    if type_ == "relance":
        if _nb_relances(session, offre_id):
            raise RelanceDejaFaite(offre_id)
        if courant is not Statut.CANDIDATURE_ENVOYEE:
            raise TransitionInvalide(f"{courant or 'nouvelle'} -> relance")
    elif courant is Statut.IGNOREE or courant in _ISSUES:
        raise TransitionInvalide(f"{courant} -> brouillon")


def enregistrer_brouillon(session: Session, offre_id: int, type_: str, contenu: str, now: datetime) -> int:
    """Enregistre le brouillon ; crée le suivi `interessante` si besoin, `relancee` après une relance."""
    verifier_brouillon(session, offre_id, type_)
    cible: Statut | None = None
    if type_ == "relance":
        cible = Statut.RELANCEE
    elif statut_de(session, offre_id) is None:
        cible = Statut.INTERESSANTE
    if cible:
        marquer(session, offre_id, cible, now)
    if type_ == "relance":
        session.execute(
            candidatures.update().where(candidatures.c.offre_id == offre_id).values(relance_le=_utc_naif(now))
        )
    candidature_id = session.execute(
        select(candidatures.c.id).where(candidatures.c.offre_id == offre_id)
    ).scalar_one()
    res = session.execute(
        brouillons.insert().values(
            candidature_id=candidature_id,
            type=type_,
            contenu=contenu,
            gmail_draft=False,
            cree_le=_utc_naif(now),
        )
    )
    return int(res.inserted_primary_key[0])  # type: ignore[attr-defined]


def lire_brouillon(session: Session, brouillon_id: int) -> BrouillonLu | None:
    ligne = session.execute(
        select(brouillons, candidatures.c.offre_id)
        .join(candidatures, brouillons.c.candidature_id == candidatures.c.id)
        .where(brouillons.c.id == brouillon_id)
    ).mappings().one_or_none()  # fmt: skip
    if ligne is None:
        return None
    return BrouillonLu(
        ligne["id"], ligne["offre_id"], ligne["type"], ligne["contenu"], bool(ligne["gmail_draft"])
    )


def marquer_depose(session: Session, brouillon_id: int) -> None:
    session.execute(brouillons.update().where(brouillons.c.id == brouillon_id).values(gmail_draft=True))


_CHAMPS_ENTREPRISE = [c for c in Entreprise.model_fields if c not in ("siret", "origine", "priorite")]


def enregistrer_entreprise(session: Session, entreprise: Entreprise, now: datetime) -> tuple[int, bool]:
    """Crée ou met à jour par SIRET ; (id, créée). Une valeur absente n'efface jamais une valeur connue.

    Jamais touchés : `listee_le`, `contactee_le`, `ignoree_le`, `origine` (celle de la création).
    La priorité ne vient que du CSV, la liste voulue par l'utilisateur.
    """
    maintenant = _utc_naif(now)
    champs = {c: getattr(entreprise, c) for c in _CHAMPS_ENTREPRISE if getattr(entreprise, c) is not None}
    if entreprise.origine == "csv" and entreprise.priorite is not None:
        champs["priorite"] = entreprise.priorite
    existante = session.execute(
        select(entreprises.c.id).where(entreprises.c.siret == entreprise.siret)
    ).scalar_one_or_none()
    if existante is None and entreprise.origine != "csv":
        # Un autre établissement d'une unité déjà connue (même SIREN) n'est pas une nouvelle entreprise.
        connue = session.execute(
            select(entreprises.c.id).where(entreprises.c.siret.like(f"{entreprise.siret[:9]}%"))
        ).scalars().first()  # fmt: skip
        if connue is not None:
            return connue, False
    if existante is None:
        res = session.execute(
            entreprises.insert().values(
                siret=entreprise.siret, origine=entreprise.origine, cree_le=maintenant,
                maj_le=maintenant, **champs,
            )
        )  # fmt: skip
        return int(res.inserted_primary_key[0]), True  # type: ignore[attr-defined]
    session.execute(
        entreprises.update().where(entreprises.c.id == existante).values(**champs, maj_le=maintenant)
    )
    return existante, False


def lire_entreprise(session: Session, entreprise_id: int) -> Entreprise:
    ligne = session.execute(select(entreprises).where(entreprises.c.id == entreprise_id)).mappings().one()
    return Entreprise(**{k: ligne[k] for k in Entreprise.model_fields})
