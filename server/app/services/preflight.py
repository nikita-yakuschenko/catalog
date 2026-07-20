"""Preflight checks before PDF assembly."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.domain.models import AssetType, Catalog, HouseProject


@dataclass
class CheckItem:
    code: str
    level: str  # info | warning | error
    message: str
    project_id: Optional[str] = None


@dataclass
class PreflightReport:
    status: str  # passed | warning | failed
    errors: list[CheckItem] = field(default_factory=list)
    warnings: list[CheckItem] = field(default_factory=list)
    checks: list[CheckItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        def ser(items: list[CheckItem]) -> list[dict]:
            return [
                {
                    "code": i.code,
                    "level": i.level,
                    "message": i.message,
                    "project_id": i.project_id,
                }
                for i in items
            ]

        return {
            "status": self.status,
            "errors": ser(self.errors),
            "warnings": ser(self.warnings),
            "checks": ser(self.checks),
        }


class PreflightService:
    def run(self, catalog: Catalog, projects: list[HouseProject]) -> PreflightReport:
        report = PreflightReport(status="passed")
        if not projects:
            self._add(report, "no_projects", "error", "В каталоге нет проектов")

        for project in projects:
            pid = str(project.id)
            assets = [a for a in project.assets if not a.excluded]
            exteriors = [a for a in assets if a.type == AssetType.exterior]
            plans = [a for a in assets if a.type == AssetType.floor_plan]

            if not exteriors:
                self._add(report, "missing_exterior", "error", f"Нет экстерьера: {project.short_name}", pid)
            if not plans:
                self._add(report, "missing_plan", "error", f"Нет планировки: {project.short_name}", pid)
            if project.area is None:
                self._add(report, "missing_area", "error", f"Нет площади: {project.short_name}", pid)
            if not project.dimensions_display and (
                project.dimensions_width is None or project.dimensions_depth is None
            ):
                self._add(report, "missing_dimensions", "error", f"Нет габаритов: {project.short_name}", pid)

            if catalog.show_prices and not project.price:
                self._add(
                    report,
                    "missing_price",
                    "warning",
                    f"Нет цены при включённом show_prices: {project.short_name}",
                    pid,
                )
            if catalog.show_prices and not catalog.price_actual_at:
                self._add(report, "missing_price_date", "warning", "Не указана дата актуальности цен")

            for asset in exteriors + plans:
                if not asset.local_path or not Path(asset.local_path).exists():
                    self._add(
                        report,
                        "missing_file",
                        "error",
                        f"Файл недоступен: {asset.source_url}",
                        pid,
                    )
                    continue
                if asset.quality_status.value == "error":
                    self._add(report, "broken_image", "error", f"Повреждённое изображение: {project.short_name}", pid)
                elif asset.width and asset.width < 1000:
                    self._add(
                        report,
                        "low_resolution",
                        "warning",
                        f"Низкое разрешение ({asset.width}px): {project.short_name}",
                        pid,
                    )

        if report.errors:
            report.status = "failed"
        elif report.warnings:
            report.status = "warning"
        else:
            report.status = "passed"
        return report

    def _add(
        self,
        report: PreflightReport,
        code: str,
        level: str,
        message: str,
        project_id: Optional[str] = None,
    ) -> None:
        item = CheckItem(code=code, level=level, message=message, project_id=project_id)
        report.checks.append(item)
        if level == "error":
            report.errors.append(item)
        elif level == "warning":
            # Deduplicate identical warnings without project
            if not any(w.code == code and w.project_id is None for w in report.warnings) or project_id:
                if project_id or not any(w.code == code for w in report.warnings):
                    report.warnings.append(item)
