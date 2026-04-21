"""ai pipeline tables: pillars, microtopics, article_ai, article_tags, article_embeddings

Revision ID: 0003_ai_tables
Revises: 0002_sources_articles
Create Date: 2026-04-20

Enables pgvector extension (required for the embeddings table's HNSW index).
On Supabase you can also enable this via dashboard → Database → Extensions.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0003_ai_tables"
down_revision: Union[str, None] = "0002_sources_articles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 384


def upgrade() -> None:
    # Enable pgvector — idempotent, safe to run even if already enabled
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Pillars: 9 top-level buckets
    op.create_table(
        "pillars",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("name_en", sa.String(100), nullable=False),
        sa.Column("name_hi", sa.String(100), nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_pillars_slug", "pillars", ["slug"], unique=True)

    # Microtopics: leaf taxonomy nodes
    op.create_table(
        "microtopics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "pillar_id",
            sa.Integer(),
            sa.ForeignKey("pillars.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("name_en", sa.String(200), nullable=False),
        sa.Column("name_hi", sa.String(200), nullable=True),
        sa.Column("prompt_gloss", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_microtopics_slug", "microtopics", ["slug"], unique=True)
    op.create_index("ix_microtopics_pillar_id", "microtopics", ["pillar_id"])

    # Article AI outputs (1:1)
    op.create_table(
        "article_ai",
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("headline_rewrite", sa.Text(), nullable=True),
        sa.Column("summary_60w", sa.Text(), nullable=True),
        sa.Column("wwww", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("key_entities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("readability_score", sa.Float(), nullable=True),
        sa.Column("ai_model_used", sa.String(100), nullable=True),
        sa.Column("prompt_version", sa.String(20), nullable=False, server_default="v1"),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Article → microtopic multi-label tags
    op.create_table(
        "article_tags",
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "microtopic_id",
            sa.Integer(),
            sa.ForeignKey("microtopics.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "pillar_id",
            sa.Integer(),
            sa.ForeignKey("pillars.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "classifier_version",
            sa.String(20),
            nullable=False,
            server_default="zs-minilm-v1",
        ),
    )
    op.create_index("ix_article_tags_pillar_id", "article_tags", ["pillar_id"])
    op.create_index(
        "ix_article_tags_microtopic_confidence",
        "article_tags",
        ["microtopic_id", "confidence"],
    )

    # Embeddings with HNSW index
    op.create_table(
        "article_embeddings",
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column(
            "model_name",
            sa.String(100),
            nullable=False,
            server_default="all-MiniLM-L6-v2",
        ),
        sa.Column(
            "embedded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # HNSW index for ANN search. Good defaults: m=16, ef_construction=64.
    op.execute(
        "CREATE INDEX ix_article_embeddings_hnsw "
        "ON article_embeddings USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_article_embeddings_hnsw")
    op.drop_table("article_embeddings")
    op.drop_index("ix_article_tags_microtopic_confidence", table_name="article_tags")
    op.drop_index("ix_article_tags_pillar_id", table_name="article_tags")
    op.drop_table("article_tags")
    op.drop_table("article_ai")
    op.drop_index("ix_microtopics_pillar_id", table_name="microtopics")
    op.drop_index("ix_microtopics_slug", table_name="microtopics")
    op.drop_table("microtopics")
    op.drop_index("ix_pillars_slug", table_name="pillars")
    op.drop_table("pillars")
    # Don't drop extension — other tables may need it later
