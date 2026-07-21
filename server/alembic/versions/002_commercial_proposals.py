"""commercial proposals

Revision ID: 002_commercial_proposals
Revises: 001_initial
Create Date: 2026-07-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_commercial_proposals"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commercial_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source",
            sa.Enum("api", "bitrix", "pdf", name="proposalsource"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(128), nullable=False, server_default=""),
        sa.Column(
            "status",
            sa.Enum("draft", "building", "ready", "failed", name="proposalstatus"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("house_projects.id", ondelete="SET NULL")),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("document", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_pdf_path", sa.String(1024), nullable=False, server_default=""),
        sa.Column("intake_markdown", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_commercial_proposals_external_id", "commercial_proposals", ["external_id"])

    op.create_table(
        "proposal_builds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "proposal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("commercial_proposals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "ready", "failed", name="buildstatus", create_type=False),
            nullable=False,
        ),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("log", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("pdf_path", sa.String(1024), nullable=False, server_default=""),
        sa.Column("html_path", sa.String(1024), nullable=False, server_default=""),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_proposal_builds_proposal_id", "proposal_builds", ["proposal_id"])


def downgrade() -> None:
    op.drop_table("proposal_builds")
    op.drop_index("ix_commercial_proposals_external_id", table_name="commercial_proposals")
    op.drop_table("commercial_proposals")
    op.execute("DROP TYPE IF EXISTS proposalsource")
    op.execute("DROP TYPE IF EXISTS proposalstatus")
