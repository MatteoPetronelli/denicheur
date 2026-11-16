import os

from alembic import context

from denicheur.db.base import make_engine
from denicheur.db.tables import metadata

config = context.config
url = config.attributes.get("url") or os.environ.get("DATABASE_URL") or "sqlite:///denicheur.db"

if context.is_offline_mode():
    context.configure(url=url, target_metadata=metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with make_engine(url).connect() as connection:
        context.configure(connection=connection, target_metadata=metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
