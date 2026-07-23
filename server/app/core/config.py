from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]  # d:/catalog


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(ROOT / ".env"), str(Path.cwd() / ".env")),
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://avgst:avgst@localhost:5436/avgst_catalog"
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    cors_origins: str = "http://localhost:3000"
    storage_dir: str = str(ROOT / "storage")
    output_dir: str = str(ROOT / "output")
    templates_dir: str = str(ROOT / "templates")

    tilda_api_base: str = "https://store.tildaapi.com/api/getproductslist/"
    tilda_modular_storepartuid: str = "211557090161"
    tilda_modular_recid: str = "1128265271"
    tilda_panel_storepartuid: str = "410948745601"
    tilda_panel_recid: str = "1128270966"

    pdf_renderer: str = "chromium"
    prince_bin: str = ""
    max_asset_size_mb: int = 25
    http_timeout_sec: int = 30
    # Skip icons / lazy placeholders when syncing (both sides must be at least this many px)
    min_asset_edge_px: int = 128
    # Max images per project from Tilda API + product page (slider gallery)
    max_sync_assets_per_project: int = 24
    bitrix_webhook_secret: str = ""
    # Incoming Bitrix REST webhook base, e.g. https://xxx.bitrix24.ru/rest/1/xxxxx/
    bitrix_rest_webhook_url: str = ""
    # Optional: UF field codes for source PDF / result KP; Disk folder for uploads
    bitrix_source_file_field: str = ""
    bitrix_result_file_field: str = ""
    bitrix_kp_folder_id: str = ""
    # SPA "База проектов" linked via parentId{N} on commercial proposal item
    bitrix_project_entity_type_id: int = 1212
    # Stage STATUS_ID for «КП Готово» (crm.status.list ENTITY_ID=DYNAMIC_{type}_STAGE_{category})
    bitrix_ready_stage_id: str = "DT1240_163:CLIENT"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
