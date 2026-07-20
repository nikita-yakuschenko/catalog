import enum
import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.db import Base


# JSON that works on Postgres (JSONB) and SQLite (JSON) for tests
JsonType = JSON().with_variant(JSONB(), "postgresql")


class Technology(str, enum.Enum):
    modular = "modular"
    panel = "panel"


class AssetType(str, enum.Enum):
    exterior = "exterior"
    floor_plan = "floor_plan"
    facade = "facade"
    section = "section"
    interior = "interior"
    detail = "detail"
    decorative = "decorative"
    unknown = "unknown"


class QualityStatus(str, enum.Enum):
    ok = "ok"
    warning = "warning"
    error = "error"


class CatalogStatus(str, enum.Enum):
    draft = "draft"
    rendering = "rendering"
    ready = "ready"
    failed = "failed"


class BuildStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    ready = "ready"
    failed = "failed"


class OutputProfile(str, enum.Enum):
    screen = "screen"
    print = "print"


class HouseProject(Base):
    __tablename__ = "house_projects"
    __table_args__ = (UniqueConstraint("source", "source_uid", name="uq_project_source"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(50), default="tilda")
    source_uid: Mapped[str] = mapped_column(String(64), index=True)
    technology: Mapped[Technology] = mapped_column(Enum(Technology), index=True)
    category: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(255))
    short_name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(160), index=True)
    area: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dimensions_width: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dimensions_depth: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dimensions_display: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    floors: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="RUB")
    description: Mapped[str] = mapped_column(Text, default="")
    features: Mapped[list] = mapped_column(JsonType, default=list)
    project_url: Mapped[str] = mapped_column(String(512), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_payload: Mapped[dict] = mapped_column(JsonType, default=dict)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    assets: Mapped[list["ProjectAsset"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProjectAsset.sort_order"
    )


class ProjectAsset(Base):
    __tablename__ = "project_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("house_projects.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[AssetType] = mapped_column(Enum(AssetType), default=AssetType.unknown)
    source_url: Mapped[str] = mapped_column(String(1024))
    local_path: Mapped[str] = mapped_column(String(1024), default="")
    mime_type: Mapped[str] = mapped_column(String(64), default="")
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    aspect_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    dpi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    quality_status: Mapped[QualityStatus] = mapped_column(
        Enum(QualityStatus), default=QualityStatus.ok
    )
    checksum: Mapped[str] = mapped_column(String(64), default="")
    excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    object_position: Mapped[str] = mapped_column(String(64), default="center center")

    project: Mapped["HouseProject"] = relationship(back_populates="assets")


class Catalog(Base):
    __tablename__ = "catalogs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[CatalogStatus] = mapped_column(Enum(CatalogStatus), default=CatalogStatus.draft)
    format: Mapped[str] = mapped_column(String(32), default="A4_landscape")
    output_profile: Mapped[OutputProfile] = mapped_column(
        Enum(OutputProfile), default=OutputProfile.screen
    )
    title: Mapped[str] = mapped_column(String(255), default="20 проектов домов")
    subtitle: Mapped[str] = mapped_column(
        String(255), default="Модульные и панельно-каркасные дома"
    )
    year: Mapped[int] = mapped_column(Integer, default=2026)
    show_prices: Mapped[bool] = mapped_column(Boolean, default=True)
    show_project_links: Mapped[bool] = mapped_column(Boolean, default=True)
    price_actual_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    show_contents: Mapped[bool] = mapped_column(Boolean, default=True)
    show_introduction: Mapped[bool] = mapped_column(Boolean, default=True)
    show_dividers: Mapped[bool] = mapped_column(Boolean, default=True)
    show_contacts: Mapped[bool] = mapped_column(Boolean, default=True)
    cover_variant: Mapped[str] = mapped_column(String(64), default="default")
    theme: Mapped[str] = mapped_column(String(64), default="avgst-default")
    layout_strategy: Mapped[str] = mapped_column(String(32), default="automatic")
    contacts: Mapped[dict] = mapped_column(JsonType, default=dict)
    settings: Mapped[dict] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    projects: Mapped[list["CatalogProject"]] = relationship(
        back_populates="catalog", cascade="all, delete-orphan", order_by="CatalogProject.order"
    )
    builds: Mapped[list["Build"]] = relationship(
        back_populates="catalog", cascade="all, delete-orphan", order_by="Build.created_at.desc()"
    )


class CatalogProject(Base):
    __tablename__ = "catalog_projects"
    __table_args__ = (UniqueConstraint("catalog_id", "project_id", name="uq_catalog_project"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogs.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("house_projects.id", ondelete="CASCADE"), index=True
    )
    order: Mapped[int] = mapped_column(Integer, default=0)
    layout_variant: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    layout_variant_override: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    custom_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    custom_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    selected_asset_ids: Mapped[list] = mapped_column(JsonType, default=list)
    page_status: Mapped[str] = mapped_column(String(32), default="ok")
    validation_messages: Mapped[list] = mapped_column(JsonType, default=list)

    catalog: Mapped["Catalog"] = relationship(back_populates="projects")
    project: Mapped["HouseProject"] = relationship()


class Build(Base):
    __tablename__ = "builds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogs.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[BuildStatus] = mapped_column(Enum(BuildStatus), default=BuildStatus.pending)
    output_profile: Mapped[OutputProfile] = mapped_column(
        Enum(OutputProfile), default=OutputProfile.screen
    )
    stage: Mapped[str] = mapped_column(String(64), default="queued")
    log: Mapped[list] = mapped_column(JsonType, default=list)
    preflight_report: Mapped[dict] = mapped_column(JsonType, default=dict)
    pdf_path: Mapped[str] = mapped_column(String(1024), default="")
    preview_dir: Mapped[str] = mapped_column(String(1024), default="")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    catalog: Mapped["Catalog"] = relationship(back_populates="builds")
