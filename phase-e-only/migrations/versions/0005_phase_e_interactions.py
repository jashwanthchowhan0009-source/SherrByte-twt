"""phase_e: interactions, feed, user profile vectors

Revision ID: 0005_phase_e
Revises: 0003_ai_tables
Create Date: 2026-04-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_phase_e"
down_revision = "0003_ai_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_interactions (
            id              BIGSERIAL,
            user_id         UUID        NOT NULL,
            article_id      UUID        NOT NULL,
            event_type      TEXT        NOT NULL,
            dwell_ms        INT         DEFAULT 0,
            scroll_pct      SMALLINT    DEFAULT 0,
            source_id       UUID,
            interacted_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, interacted_at)
        ) PARTITION BY RANGE (interacted_at)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_interactions_2026_04
            PARTITION OF user_interactions
            FOR VALUES FROM ('2026-04-01') TO ('2026-05-01')
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_interactions_2026_05
            PARTITION OF user_interactions
            FOR VALUES FROM ('2026-05-01') TO ('2026-06-01')
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_interactions_2026_06
            PARTITION OF user_interactions
            FOR VALUES FROM ('2026-06-01') TO ('2026-07-01')
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ui_user_time
            ON user_interactions (user_id, interacted_at DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ui_article
            ON user_interactions (article_id)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_topic_affinity (
            user_id         UUID    NOT NULL,
            topic_slug      TEXT    NOT NULL,
            pillar_id       INT,
            explicit_weight FLOAT   DEFAULT 0.0,
            implicit_score  FLOAT   DEFAULT 0.0,
            combined_score  FLOAT   DEFAULT 0.0,
            article_count   INT     DEFAULT 0,
            last_updated    TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, topic_slug)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_uta_user
            ON user_topic_affinity (user_id)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_profile_vectors (
            user_id         UUID    PRIMARY KEY,
            long_term_vec   vector(384),
            short_term_vec  vector(384),
            interaction_cnt INT     DEFAULT 0,
            updated_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS feed_impressions (
            user_id         UUID        NOT NULL,
            article_id      UUID        NOT NULL,
            served_at       TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, article_id)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_fi_user
            ON feed_impressions (user_id, served_at DESC)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_state (
            user_id         UUID    PRIMARY KEY,
            step            SMALLINT DEFAULT 0,
            completed_at    TIMESTAMPTZ,
            raw_selections  JSONB   DEFAULT '{}'
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS onboarding_state")
    op.execute("DROP TABLE IF EXISTS feed_impressions")
    op.execute("DROP TABLE IF EXISTS user_profile_vectors")
    op.execute("DROP TABLE IF EXISTS user_topic_affinity")
    op.execute("DROP TABLE IF EXISTS user_interactions CASCADE")
