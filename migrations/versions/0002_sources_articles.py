"""sources + articles tables

Revision ID: 0002_sources_articles
Revises: 0001_users_sessions
Create Date: 2026-04-20
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_sources_articles"
down_revision: Union[str, None] = "0001_users_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("rss_url", sa.Text(), nullable=False),
        sa.Column("homepage_url", sa.Text(), nullable=True),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("country", sa.String(5), nullable=False, server_default="IN"),
        sa.Column("iab_tier1", sa.String(100), nullable=True),
        sa.Column("bias_score", sa.Float(), nullable=True),
        sa.Column("factuality_score", sa.Float(), nullable=True),
        sa.Column("priority_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "consecutive_errors", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_sources_slug", "sources", ["slug"], unique=True)
    op.create_index("ix_sources_domain", "sources", ["domain"])

    op.create_table(
        "articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("simhash", sa.BigInteger(), nullable=True),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "is_editorial_pick",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("view_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("save_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("share_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_articles_url", "articles", ["url"], unique=True)
    op.create_index("ix_articles_source_id", "articles", ["source_id"])
    op.create_index("ix_articles_content_hash", "articles", ["content_hash"])
    op.create_index("ix_articles_published_at_desc", "articles", ["published_at"])
    op.create_index(
        "ix_articles_source_published", "articles", ["source_id", "published_at"]
    )
    op.create_index("ix_articles_simhash", "articles", ["simhash"])
    op.create_index("ix_articles_cluster_id", "articles", ["cluster_id"])


def downgrade() -> None:
    op.drop_index("ix_articles_cluster_id", table_name="articles")
    op.drop_index("ix_articles_simhash", table_name="articles")
    op.drop_index("ix_articles_source_published", table_name="articles")
    op.drop_index("ix_articles_published_at_desc", table_name="articles")
    op.drop_index("ix_articles_content_hash", table_name="articles")
    op.drop_index("ix_articles_source_id", table_name="articles")
    op.drop_index("ix_articles_url", table_name="articles")
    op.drop_table("articles")
    op.drop_index("ix_sources_domain", table_name="sources")
    op.drop_index("ix_sources_slug", table_name="sources")
    op.drop_table("sources")
