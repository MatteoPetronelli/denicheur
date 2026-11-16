from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

metadata = MetaData()

offres = Table(
    "offres", metadata,
    Column("id", Integer, primary_key=True),
    Column("source", String, nullable=False),
    Column("source_id", String, nullable=False),
    Column("url", String, nullable=False, unique=True),
    Column("cle_dedup", String(64), nullable=False),
    Column("titre", String, nullable=False),
    Column("entreprise", String),
    Column("commune", String),
    Column("lat", Float),
    Column("lon", Float),
    Column("distance_km", Float),
    Column("lieu_a_verifier", Boolean, nullable=False, default=False),
    Column("piste", String, nullable=False),
    Column("duree_mois", Integer),
    Column("debut", Date),
    Column("debut_des_que_possible", Boolean, nullable=False, default=False),
    Column("niveau_diplome", String),
    Column("description", Text, nullable=False),
    Column("publiee_le", DateTime),
    Column("expire_le", DateTime),
    Column("motif_rejet", String),
    Column("vue_le", DateTime, nullable=False),
    Column("notifiee_le", DateTime),
    Index("uq_offres_source", "source", "source_id", unique=True),
    Index("ix_offres_cle_dedup", "cle_dedup"),
)  # fmt: skip

scores = Table(
    "scores", metadata,
    Column("offre_id", Integer, ForeignKey("offres.id"), primary_key=True),
    Column("piste", String, nullable=False),
    Column("score", Integer, nullable=False),
    Column("points_forts", JSON, nullable=False),
    Column("points_faibles", JSON, nullable=False),
    Column("alerte", String),
    Column("projet_a_citer", String, nullable=False),
    Column("resume", Text, nullable=False),
    Column("modele", String, nullable=False),
    Column("prompt_tokens", Integer, nullable=False),
    Column("output_tokens", Integer, nullable=False),
    Column("duree_s", Float, nullable=False),
    Column("cree_le", DateTime, nullable=False),
)  # fmt: skip

candidatures = Table(
    "candidatures", metadata,
    Column("id", Integer, primary_key=True),
    Column("offre_id", Integer, ForeignKey("offres.id")),
    Column("entreprise_id", Integer),  # FK ajoutée en C6
    Column("statut", String, nullable=False),
    Column("envoyee_le", DateTime),
    Column("rappel_le", DateTime),
    Column("relance_le", DateTime),
    Column("notes", Text),
    Column("cree_le", DateTime, nullable=False),
    Column("maj_le", DateTime, nullable=False),
)  # fmt: skip

brouillons = Table(
    "brouillons", metadata,
    Column("id", Integer, primary_key=True),
    Column("candidature_id", Integer, ForeignKey("candidatures.id"), nullable=False),
    Column("type", String, nullable=False),
    Column("contenu", Text, nullable=False),
    Column("gmail_draft", Boolean, nullable=False, default=False),
    Column("cree_le", DateTime, nullable=False),
)  # fmt: skip

executions = Table(
    "executions", metadata,
    Column("id", Integer, primary_key=True),
    Column("debut", DateTime, nullable=False),
    Column("fin", DateTime),
    Column("mode", String, nullable=False),
    Column("offres_collectees", Integer, nullable=False, default=0),
    Column("offres_retenues", Integer, nullable=False, default=0),
    Column("offres_scorees", Integer, nullable=False, default=0),
    Column("offres_notifiees", Integer, nullable=False, default=0),
    Column("erreurs", JSON, nullable=False, default=list),
    Column("duree_llm_s", Float, nullable=False, default=0.0),
)  # fmt: skip

parametres = Table(
    "parametres", metadata,
    Column("cle", String, primary_key=True),
    Column("valeur", Text, nullable=False),
)  # fmt: skip
