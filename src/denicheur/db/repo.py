"""Toutes les écritures/lectures SQL passent ici (pas de session brute dans le pipeline)."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from denicheur.db.tables import candidatures, executions, offres, parametres, scores
from denicheur.models import Offre, ScoreLLM, Statut

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
