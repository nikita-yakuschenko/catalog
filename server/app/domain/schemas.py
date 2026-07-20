from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import (
    AssetType,
    BuildStatus,
    CatalogStatus,
    OutputProfile,
    QualityStatus,
    Technology,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AssetOut(ORMModel):
    id: UUID
    project_id: UUID
    type: AssetType
    source_url: str
    local_path: str
    mime_type: str
    width: int
    height: int
    aspect_ratio: float
    file_size: int
    dpi: Optional[int]
    sort_order: int
    is_primary: bool
    quality_status: QualityStatus
    checksum: str
    excluded: bool
    object_position: str


class AssetUpdate(BaseModel):
    type: Optional[AssetType] = None
    is_primary: Optional[bool] = None
    sort_order: Optional[int] = None
    excluded: Optional[bool] = None
    object_position: Optional[str] = None


class ProjectOut(ORMModel):
    id: UUID
    source: str
    source_uid: str
    technology: Technology
    category: str
    name: str
    short_name: str
    slug: str
    area: Optional[float]
    dimensions_width: Optional[float]
    dimensions_depth: Optional[float]
    dimensions_display: Optional[str]
    floors: Optional[int]
    bedrooms: Optional[int]
    bathrooms: Optional[str]
    price: Optional[int]
    currency: str
    description: str
    features: list[Any]
    project_url: str
    sort_order: int
    active: bool
    last_synced_at: Optional[datetime]
    assets: list[AssetOut] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    short_name: Optional[str] = None
    area: Optional[float] = None
    dimensions_width: Optional[float] = None
    dimensions_depth: Optional[float] = None
    dimensions_display: Optional[str] = None
    floors: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[str] = None
    price: Optional[int] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class CatalogProjectIn(BaseModel):
    project_id: UUID
    order: int = 0
    layout_variant_override: Optional[str] = None
    custom_title: Optional[str] = None


class CatalogProjectOut(ORMModel):
    id: UUID
    catalog_id: UUID
    project_id: UUID
    order: int
    layout_variant: Optional[str]
    layout_variant_override: Optional[str]
    custom_title: Optional[str]
    custom_description: Optional[str]
    selected_asset_ids: list[Any]
    page_status: str
    validation_messages: list[Any]
    project: Optional[ProjectOut] = None


class CatalogCreate(BaseModel):
    name: str
    title: str = "20 проектов домов"
    subtitle: str = "Модульные и панельно-каркасные дома"
    year: int = 2026
    format: str = "A4_landscape"
    output_profile: OutputProfile = OutputProfile.screen
    show_prices: bool = True
    show_project_links: bool = True
    price_actual_at: Optional[date] = None
    show_contents: bool = True
    show_introduction: bool = True
    show_dividers: bool = True
    show_contacts: bool = True
    cover_variant: str = "default"
    theme: str = "avgst-default"
    layout_strategy: str = "automatic"
    contacts: dict[str, Any] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict)
    project_ids: list[UUID] = Field(default_factory=list)


class CatalogUpdate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    year: Optional[int] = None
    format: Optional[str] = None
    output_profile: Optional[OutputProfile] = None
    show_prices: Optional[bool] = None
    show_project_links: Optional[bool] = None
    price_actual_at: Optional[date] = None
    show_contents: Optional[bool] = None
    show_introduction: Optional[bool] = None
    show_dividers: Optional[bool] = None
    show_contacts: Optional[bool] = None
    cover_variant: Optional[str] = None
    theme: Optional[str] = None
    layout_strategy: Optional[str] = None
    contacts: Optional[dict[str, Any]] = None
    settings: Optional[dict[str, Any]] = None


class CatalogOut(ORMModel):
    id: UUID
    name: str
    status: CatalogStatus
    format: str
    output_profile: OutputProfile
    title: str
    subtitle: str
    year: int
    show_prices: bool
    show_project_links: bool
    price_actual_at: Optional[date]
    show_contents: bool
    show_introduction: bool
    show_dividers: bool
    show_contacts: bool
    cover_variant: str
    theme: str
    layout_strategy: str
    contacts: dict[str, Any]
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    projects: list[CatalogProjectOut] = Field(default_factory=list)


class ReorderItem(BaseModel):
    project_id: UUID
    order: int


class CatalogProjectUpdate(BaseModel):
    layout_variant_override: Optional[str] = None
    custom_title: Optional[str] = None
    custom_description: Optional[str] = None
    selected_asset_ids: Optional[list[UUID]] = None


class BuildOut(ORMModel):
    id: UUID
    catalog_id: UUID
    status: BuildStatus
    output_profile: OutputProfile
    stage: str
    log: list[Any]
    preflight_report: dict[str, Any]
    pdf_path: str
    preview_dir: str
    page_count: int
    error_message: str
    created_at: datetime
    finished_at: Optional[datetime]


class SyncResult(BaseModel):
    modular_count: int
    panel_count: int
    created: int
    updated: int
    assets_downloaded: int
    errors: list[str] = Field(default_factory=list)
