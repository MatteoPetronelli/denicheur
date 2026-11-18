"""entreprises et SIRET des offres

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-18 13:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entreprises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("siret", sa.String(length=14), nullable=False),
        sa.Column("nom", sa.String(), nullable=False),
        sa.Column("activite", sa.String(), nullable=True),
        sa.Column("naf", sa.String(), nullable=True),
        sa.Column("effectif", sa.String(), nullable=True),
        sa.Column("adresse", sa.String(), nullable=True),
        sa.Column("commune", sa.String(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("distance_km", sa.Float(), nullable=True),
        sa.Column("priorite", sa.Integer(), nullable=True),
        sa.Column("url_candidature", sa.String(), nullable=True),
        sa.Column("origine", sa.String(), nullable=False),
        sa.Column("listee_le", sa.DateTime(), nullable=True),
        sa.Column("contactee_le", sa.DateTime(), nullable=True),
        sa.Column("ignoree_le", sa.DateTime(), nullable=True),
        sa.Column("cree_le", sa.DateTime(), nullable=False),
        sa.Column("maj_le", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("siret"),
    )
    # SQLite ne sait pas ajouter une clé étrangère par ALTER : la table est recopiée avec ses données.
    with op.batch_alter_table("candidatures") as batch:
        batch.create_foreign_key("fk_candidatures_entreprise", "entreprises", ["entreprise_id"], ["id"])
        batch.create_index("uq_candidatures_entreprise", ["entreprise_id"], unique=True)
    with op.batch_alter_table("offres") as batch:
        batch.add_column(sa.Column("siret", sa.String(length=14), nullable=True))
        batch.create_index("ix_offres_siret", ["siret"])


def downgrade() -> None:
    with op.batch_alter_table("offres") as batch:
        batch.drop_index("ix_offres_siret")
        batch.drop_column("siret")
    with op.batch_alter_table("candidatures") as batch:
        batch.drop_index("uq_candidatures_entreprise")
        batch.drop_constraint("fk_candidatures_entreprise", type_="foreignkey")
    op.drop_table("entreprises")
