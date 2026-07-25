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
    # SPA «Коммерческое предложение» — обрабатываем только этот entityTypeId
    bitrix_kp_entity_type_id: int = 1240
    # SPA "База проектов" linked via parentId{N} on commercial proposal item
    bitrix_project_entity_type_id: int = 1212
    # Stage STATUS_ID for «КП Готово» (crm.status.list ENTITY_ID=DYNAMIC_{type}_STAGE_{category})
    bitrix_ready_stage_id: str = "DT1240_163:CLIENT"
    # КП SPA: регион поставки + стоимость доставки (crm.item.get useOriginalUfNames=Y)
    bitrix_region_field: str = "UF_CRM_129_1784903637"
    bitrix_delivery_price_field: str = "UF_CRM_129_1784904416453"

    # Bitrix24 OAuth (локальное приложение) — вход в UI каталога
    # Если client_id пуст — авторизация отключена (удобно для локальной разработки)
    bitrix_oauth_client_id: str = ""
    bitrix_oauth_client_secret: str = ""
    # Портал без слэша: https://avgstroy.bitrix24.ru
    bitrix_portal_url: str = "https://avgstroy.bitrix24.ru"
    # Публичный URL приложения (куда редиректим после логина), без слэша
    app_public_url: str = "http://localhost:3000"
    # Callback должен совпадать с Redirect URI в настройках локального приложения Bitrix
    # Пример: https://catalog.avgst.ru/api/auth/bitrix/callback
    bitrix_oauth_redirect_uri: str = ""
    # Секрет подписи cookie-сессии (если пуст — берём client_secret)
    auth_session_secret: str = ""
    # Срок жизни сессии UI, секунды (7 дней)
    auth_session_ttl_sec: int = 60 * 60 * 24 * 7

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def auth_enabled(self) -> bool:
        return bool(self.bitrix_oauth_client_id.strip())

    @property
    def session_secret(self) -> str:
        return (self.auth_session_secret or self.bitrix_oauth_client_secret or "dev-insecure").strip()

    @property
    def oauth_redirect_uri(self) -> str:
        explicit = self.bitrix_oauth_redirect_uri.strip()
        if explicit:
            return explicit
        base = self.app_public_url.rstrip("/")
        return f"{base}/api/auth/bitrix/callback"


settings = Settings()
