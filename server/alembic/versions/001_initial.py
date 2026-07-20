"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-07-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "house_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_uid", sa.String(64), nullable=False),
        sa.Column("technology", sa.Enum("modular", "panel", name="technology"), nullable=False),
        sa.Column("category", sa.String(120), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("short_name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("area", sa.Float(), nullable=True),
        sa.Column("dimensions_width", sa.Float(), nullable=True),
        sa.Column("dimensions_depth", sa.Float(), nullable=True),
        sa.Column("dimensions_display", sa.String(64), nullable=True),
        sa.Column("floors", sa.Integer(), nullable=True),
        sa.Column("bedrooms", sa.Integer(), nullable=True),
        sa.Column("bathrooms", sa.String(32), nullable=True),
        sa.Column("price", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("features", postgresql.JSONB(), nullable=False),
        sa.Column("project_url", sa.String(512), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("source_payload", postgresql.JSONB(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source", "source_uid", name="uq_project_source"),
    )
    op.create_index("ix_house_projects_source_uid", "house_projects", ["source_uid"])
    op.create_index("ix_house_projects_technology", "house_projects", ["technology"])
    op.create_index("ix_house_projects_slug", "house_projects", ["slug"])

    op.create_table(
        "project_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("house_projects.id", ondelete="CASCADE")),
        sa.Column(
            "type",
            sa.Enum(
                "exterior",
                "floor_plan",
                "facade",
                "section",
                "interior",
                "detail",
                "decorative",
                "unknown",
                name="assettype",
            ),
            nullable=False,
        ),
        sa.Column("source_url", sa.String(1024), nullable=False),
        sa.Column("local_path", sa.String(1024), nullable=False),
        sa.Column("mime_type", sa.String(64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("aspect_ratio", sa.Float(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("dpi", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("quality_status", sa.Enum("ok", "warning", "error", name="qualitystatus"), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("excluded", sa.Boolean(), nullable=False),
        sa.Column("object_position", sa.String(64), nullable=False),
    )
    op.create_index("ix_project_assets_project_id", "project_assets", ["project_id"])

    op.create_table(
        "catalogs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.Enum("draft", "rendering", "ready", "failed", name="catalogstatus"), nullable=False),
        sa.Column("format", sa.String(32), nullable=False),
        sa.Column("output_profile", sa.Enum("screen", "print", name="outputprofile"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("subtitle", sa.String(255), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("show_prices", sa.Boolean(), nullable=False),
        sa.Column("show_project_links", sa.Boolean(), nullable=False),
        sa.Column("price_actual_at", sa.Date(), nullable=True),
        sa.Column("show_contents", sa.Boolean(), nullable=False),
        sa.Column("show_introduction", sa.Boolean(), nullable=False),
        sa.Column("show_dividers", sa.Boolean(), nullable=False),
        sa.Column("show_contacts", sa.Boolean(), nullable=False),
        sa.Column("cover_variant", sa.String(64), nullable=False),
        sa.Column("theme", sa.String(64), nullable=False),
        sa.Column("layout_strategy", sa.String(32), nullable=False),
        sa.Column("contacts", postgresql.JSONB(), nullable=False),
        sa.Column("settings", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "catalog_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("catalog_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("catalogs.id", ondelete="CASCADE")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("house_projects.id", ondelete="CASCADE")),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("layout_variant", sa.String(64), nullable=True),
        sa.Column("layout_variant_override", sa.String(64), nullable=True),
        sa.Column("custom_title", sa.String(255), nullable=True),
        sa.Column("custom_description", sa.Text(), nullable=True),
        sa.Column("selected_asset_ids", postgresql.JSONB(), nullable=False),
        sa.Column("page_status", sa.String(32), nullable=False),
        sa.Column("validation_messages", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("catalog_id", "project_id", name="uq_catalog_project"),
    )

    op.create_table(
        "builds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("catalog_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("catalogs.id", ondelete="CASCADE")),
        sa.Column("status", sa.Enum("pending", "running", "ready", "failed", name="buildstatus"), nullable=False),
        sa.Column("output_profile", sa.Enum("screen", "print", name="outputprofile", create_type=False), nullable=False),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("log", postgresql.JSONB(), nullable=False),
        sa.Column("preflight_report", postgresql.JSONB(), nullable=False),
        sa.Column("pdf_path", sa.String(1024), nullable=False),
        sa.Column("preview_dir", sa.String(1024), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("builds")
    op.drop_table("catalog_projects")
    op.drop_table("catalogs")
    op.drop_table("project_assets")
    op.drop_table("house_projects")
    for name in (
        "buildstatus",
        "catalogstatus",
        "outputprofile",
        "qualitystatus",
        "assettype",
        "technology",
    ):
        op.execute(f"DROP TYPE IF EXISTS {name}")
