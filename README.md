# AVGST Catalog Builder

Система сборки PDF-каталогов проектов домов [AVGST](https://avgst.ru/): синхронизация с Tilda Store API, нормализация характеристик, HTML/CSS верстка (Paged Media) и генерация screen PDF через Playwright/Chromium.

## Архитектура

- `client/` — Next.js (App Router), TypeScript, Tailwind
- `server/` — FastAPI, SQLAlchemy, Alembic, Jinja2, Playwright
- `templates/` — HTML/CSS тема `avgst-default` и layouts
- `storage/` — скачанные изображения проектов
- `output/` — PDF, page previews, preflight-отчёты

```
Tilda API → sync → PostgreSQL + storage
                 ↓
        Catalog config (API/UI/CLI)
                 ↓
   LayoutSelector → Jinja2 HTML → Chromium PDF
```

## Локальный запуск

### 1. Переменные окружения

```powershell
Copy-Item .env.example .env
```

Для локального запуска без Docker поправьте в `.env`:

- `DATABASE_URL=postgresql+asyncpg://avgst:avgst@localhost:5436/avgst_catalog`
- `STORAGE_DIR`, `OUTPUT_DIR`, `TEMPLATES_DIR` — абсолютные пути к папкам репозитория

### 2. PostgreSQL

```powershell
docker compose up -d postgres
```

### 3. Backend

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
$env:PYTHONPATH = (Get-Location).Path
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend

```powershell
cd client
npm install
npm run dev
```

Откройте http://localhost:3000

### 5. Публичный URL для тестов (cloudflared)

Нужны запущенные backend (`:8000`) и frontend (`:3000`). Next проксирует `/api`, `/storage`, `/output` на backend — достаточно одного туннеля на UI.

```powershell
winget install --id Cloudflare.cloudflared -e
cloudflared tunnel --url http://localhost:3000
```

В выводе будет URL вида `https://….trycloudflare.com`. Откройте его в браузере (или отправьте коллеге). URL меняется при каждом запуске — для разовых тестов этого достаточно.

`NEXT_PUBLIC_API_URL` оставьте пустым (same-origin). Если в `.env` ещё стоит `http://localhost:8000`, уберите или закомментируйте и перезапустите `npm run dev`.

### Docker Compose (полный стек)

```powershell
docker compose up --build
```

- UI: http://localhost:3000
- API: http://localhost:8000/docs

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `DATABASE_URL` | PostgreSQL async URL |
| `TILDA_*` | storepartuid / recid разделов каталога |
| `STORAGE_DIR` / `OUTPUT_DIR` / `TEMPLATES_DIR` | пути данных |
| `NEXT_PUBLIC_API_URL` | URL API для клиента; пусто = same-origin через Next proxy |
| `BACKEND_URL` | Куда Next проксирует `/api` (по умолчанию `http://127.0.0.1:8000`) |
| `PRINCE_BIN` | путь к PrinceXML (опционально) |

## Синхронизация Tilda

UI: кнопка «Синхронизировать с Tilda» на `/projects`.

CLI:

```powershell
cd server
$env:PYTHONPATH = (Get-Location).Path
python -m app.cli sync-projects
```

## Создание каталога

1. UI: `/catalogs/new` → выбрать проекты (кнопка «Как в примере 10+10») → создать.
2. Preflight → «Собрать PDF» → превью / скачивание.

CLI:

```powershell
python -m app.cli create-catalog
python -m app.cli preflight <catalog_id>
python -m app.cli render <catalog_id>
python -m app.cli render <catalog_id> --profile print
```

## Layouts

Рабочий layout по умолчанию:

1. `project_spread` — **2 страницы на проект**
   - страница 1: крупный экстерьер, цена, QR/ссылка на avgst.ru
   - страница 2: планировки, доп. ракурсы, характеристики с иконками, цена, CTA

Legacy (только через ручной override):

2. `hero_plan_right`
3. `split_equal`

`hero_top_plan_bottom` отключён (на A4 landscape давал наложения).

## Screen / Print

- **screen** — Chromium, RGB, без bleed
- **print** — если PrinceXML не установлен, используется Chromium + warning в preflight: PDF не сертифицирован как PDF/X-4

## Ограничения Chromium

- Нет нативного PDF/X / CMYK
- CSS Paged Media поддерживается частично; каталог верстается как последовательность `.page` фиксированного A4 landscape
- Шрифты зависят от системы контейнера / хоста

## Подключение PrinceXML

Укажите `PRINCE_BIN` в `.env`. Адаптер: `server/app/renderers/print_renderer.py`.

## Структура output

```
output/{catalog_id}/{build_id}/
  catalog.html
  catalog.pdf
  preflight-report.json
  pages/page-001.jpg
```

## Тесты

```powershell
cd server
$env:PYTHONPATH = (Get-Location).Path
pytest -q
```

## API (основное)

- `POST /api/sync/tilda`
- `GET /api/projects`
- `POST /api/catalogs`
- `POST /api/catalogs/{id}/preflight`
- `POST /api/catalogs/{id}/build`
- `GET /api/catalogs/{id}/preview`
- `GET /api/catalogs/{id}/download`

Полный список — `/docs`.

## Коммерческие предложения (КП)

Помимо PDF-каталогов, сервис собирает **коммерческие предложения** (A4, портрет) из:

1. **Структурированного JSON** (основной сценарий для Bitrix24).
2. **PDF-сметы** (например, `example.pdf`) — текст извлекается через [MarkItDown](https://github.com/microsoft/markitdown), при недоступности библиотеки используется PyMuPDF.
3. **Слияния** обоих источников: поля из API/Bitrix имеют приоритет, PDF заполняет пробелы (название проекта, комплектация, цены, опции).

Миграция БД:

```powershell
cd server
$env:PYTHONPATH = (Get-Location).Path
alembic upgrade head
```

### API

| Метод | Назначение |
|--------|------------|
| `POST /api/proposals` | КП из JSON |
| `POST /api/proposals/bitrix` | Вебхук Bitrix24 (заголовок `X-Bitrix-Webhook-Secret`, если задан `BITRIX_WEBHOOK_SECRET`) |
| `POST /api/proposals/from-pdf` | `multipart`: файл PDF + опционально `payload_json` |
| `POST /api/proposals/{id}/build` | Сборка PDF (фон) |
| `GET /api/proposals/{id}/status` | Статус сборки |
| `GET /api/proposals/{id}/download` | Скачать готовый PDF |

Пример тела для Bitrix (`POST /api/proposals/bitrix`):

```json
{
  "deal_id": "D_12845",
  "project_name": "Зимний 54",
  "package_name": "Базовая",
  "house_price": 2768000,
  "options": [
    { "title": "Внешняя отделка блок-хаус", "price": 221000 }
  ],
  "client": { "name": "Иван Иванов", "phone": "+7..." },
  "manager": { "name": "Менеджер", "phone": "+7..." }
}
```

Исходящее событие Bitrix (`ONCRMDYNAMICITEMADD` и т.п.) тоже принимается: сервер по `ENTITY_TYPE_ID` + `ID` дергает входящий REST (`BITRIX_REST_WEBHOOK_URL`) → `crm.item.get`, скачивает исходный файл с Диска, прогоняет через MarkItDown, собирает КП и при наличии `BITRIX_KP_FOLDER_ID` (или папки исходника) заливает PDF обратно на Диск.

По `project_name` выполняется привязка к проекту в каталоге (для фото в КП). Результат: `output/proposals/{id}/{build_id}/proposal.pdf`.
