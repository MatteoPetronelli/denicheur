"""Crée une base de test migrée par Alembic : le schéma reste défini par Python seulement."""

import sys

from denicheur.db.base import migrer

migrer(f"sqlite:///{sys.argv[1]}")
