from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import Engine, create_engine, event

RACINE = Path(__file__).resolve().parents[3]


def normaliser_url(url: str) -> str:
    for prefixe in ("postgres://", "postgresql://"):
        if url.startswith(prefixe):
            return "postgresql+psycopg://" + url[len(prefixe) :]
    return url


def make_engine(url: str) -> Engine:
    engine = create_engine(normaliser_url(url))
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _wal(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA journal_mode=WAL")

    return engine


def migrer(url: str) -> None:
    """Applique les migrations Alembic (`init-db`)."""
    cfg = AlembicConfig(str(RACINE / "alembic.ini"))
    cfg.set_main_option("script_location", str(RACINE / "migrations"))
    cfg.attributes["url"] = url
    command.upgrade(cfg, "head")
