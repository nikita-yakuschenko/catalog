# Деплой AVGST Catalog Builder на Dokploy

Инструкция по развёртыванию проекта (FastAPI-сервер + Next.js-клиент) на VPS с Dokploy.
Postgres создаётся отдельным сервисом Dokploy, приложение поднимается из `docker-compose.dokploy.yml`.

## Что потребуется

- VPS с установленным Dokploy (панель доступна по `http://IP:3000`)
- Домен (например `catalog.example.ru`) с доступом к DNS
- Доступ к GitHub-репозиторию `nikita-yakuschenko/catalog`
- Данные Bitrix24: URL входящего REST-вебхука, ID смарт-процессов

## Архитектура на сервере

```
Интернет → Traefik (Dokploy, 443) → client:3000 (Next.js)
                                        │  rewrites /api, /storage, /output, /health
                                        ▼
                                    server:8000 (FastAPI + Chromium)
                                        │
                                        ▼
                                    Postgres (отдельный сервис Dokploy)
```

Браузер и Bitrix ходят только на домен клиента; всё `/api/*` проксируется внутрь к серверу.
Поэтому `NEXT_PUBLIC_API_URL` остаётся **пустым** — менять не нужно.

---

## Шаг 0. Запушить код в GitHub

Dokploy собирает образы из репозитория, поэтому все локальные изменения должны быть закоммичены и запушены:

```powershell
cd d:\catalog
git add -A
git commit -m "Dokploy deploy: prod dockerfiles, compose, KP entity filter"
git push origin master
```

Проверьте, что в репозитории есть: `docker-compose.dokploy.yml`, `server/Dockerfile.prod`, `client/Dockerfile.prod`, `.dockerignore`, `client/.dockerignore`.

## Шаг 1. Создать Postgres в Dokploy

1. В проекте Dokploy: **Create Service → Database → PostgreSQL**.
2. Имя: `avgst-catalog-db`, база `avgst_catalog`, пользователь `avgst`, пароль — сгенерировать и сохранить.
3. После запуска откройте вкладку базы и скопируйте **Internal Connection / Internal Host** — имя хоста внутри `dokploy-network` (например `avgst-catalog-db-xxxxxx`). Порт — `5432`.
4. External-порт наружу НЕ открывать (не нужен).

## Шаг 2. Создать Compose-сервис приложения

1. **Create Service → Compose**, тип **Docker Compose**.
2. Provider: **GitHub** (или Git с URL `https://github.com/nikita-yakuschenko/catalog.git`), ветка `master`.
3. **Compose Path**: `./docker-compose.dokploy.yml`.

## Шаг 3. Заполнить Environment

Вкладка **Environment** compose-сервиса (Dokploy сам запишет это в `.env` рядом с compose-файлом):

```env
# Обязательно: internal host из шага 1
DATABASE_URL=postgresql+asyncpg://avgst:ПАРОЛЬ@INTERNAL_HOST:5432/avgst_catalog

# Домен клиента (для CORS; при same-origin прокси можно оставить *)
CORS_ORIGINS=https://catalog.example.ru

# Bitrix24
BITRIX_REST_WEBHOOK_URL=https://avgstroy.bitrix24.ru/rest/1/XXXXXXXX/
BITRIX_WEBHOOK_SECRET=придумайте-длинный-секрет
BITRIX_KP_ENTITY_TYPE_ID=1240
BITRIX_PROJECT_ENTITY_TYPE_ID=1212
BITRIX_READY_STAGE_ID=DT1240_163:CLIENT
BITRIX_REGION_FIELD=UF_CRM_129_1784903637
BITRIX_DELIVERY_PRICE_FIELD=UF_CRM_129_1784904416453
# Опционально (если используются):
# BITRIX_SOURCE_FILE_FIELD=
# BITRIX_RESULT_FILE_FIELD=
# BITRIX_KP_FOLDER_ID=
```

Tilda-параметры (`TILDA_*`) задавать не нужно — рабочие значения зашиты по умолчанию в `server/app/core/config.py`.

## Шаг 4. Первый деплой

1. Нажмите **Deploy** и следите за логами сборки.
2. Сервер собирается из образа Playwright (~2 ГБ, Chromium уже внутри) — первый билд занимает 5–15 минут.
3. При старте сервер сам выполняет миграции (`alembic upgrade head`) — отдельно ничего запускать не нужно.

> Если сборка клиента падает по памяти (Next.js build на VPS < 2 ГБ RAM) — добавьте swap на сервере:
> `sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile`

## Шаг 5. Подключить домен

1. В DNS домена создайте **A-запись** на IP VPS.
2. В compose-сервисе: вкладка **Domains → Add Domain**:
   - Host: `catalog.example.ru`
   - Service Name: `client`
   - Container Port: `3000`
   - HTTPS: включить, сертификат **Let's Encrypt**
3. Подождите выпуск сертификата (~1 минута).

## Шаг 6. Проверка

```powershell
# API жив (проксируется через клиент к серверу)
curl https://catalog.example.ru/health

# UI открывается
start https://catalog.example.ru
```

Далее в UI: страница «Проекты» → «Синхронизировать с Tilda» (выполняется в фоне) → проекты и изображения появляются.

## Шаг 7. Настроить Bitrix24

1. **Исходящий вебхук** (Bitrix → приложение): Разработчикам → Другое → Исходящий вебхук:
   - Событие: `ONCRMDYNAMICITEMADD` (создание элемента смарт-процесса)
   - URL: `https://catalog.example.ru/api/proposals/bitrix`
   - Заголовок `X-Bitrix-Webhook-Secret` = значение `BITRIX_WEBHOOK_SECRET` (если задавали)
2. Входящий REST-вебхук уже указан в `BITRIX_REST_WEBHOOK_URL` (шаг 3) — по нему сервер читает элемент, контакт, файлы Диска и выгружает готовое КП.
3. События от любых смарт-процессов, кроме «Коммерческое предложение» (`entityTypeId` ≠ `BITRIX_KP_ENTITY_TYPE_ID`), сервер отвечает `200 {"status":"ignored"}` и ничего не запускает.

Тест: создайте элемент в СП «Коммерческое предложение» с прикреплённым PDF → в UI на странице предложений появится запись и запустится сборка КП.

## Обновления

- Вручную: `git push` → кнопка **Deploy** в Dokploy.
- Автоматически: вкладка **Deployments → Auto Deploy** — Dokploy даст webhook-URL, добавьте его в GitHub (Settings → Webhooks) — деплой на каждый push.

Данные при редеплое сохраняются: `storage_data` и `output_data` — именованные Docker-volumes, база — отдельный сервис.

## Типовые проблемы

| Симптом | Причина | Решение |
|---|---|---|
| Сервер падает на старте: `could not translate host name` | Неверный `DATABASE_URL` / хост БД | Скопировать Internal Host из вкладки базы; проверить, что в compose есть `dokploy-network` (уже добавлена) |
| Домен отдаёт 404/502 | Traefik не видит сервис | В Domains указан Service `client`, порт `3000`; сервисы в `dokploy-network` |
| Bitrix-вебхук не доходит | HTTP вместо HTTPS, либо URL без `/api` | URL строго `https://ДОМЕН/api/proposals/bitrix` |
| В ответ на вебхук `{"status":"ignored"}` | Событие от другого смарт-процесса | Это норма; если игнорируется нужный СП — сверить `BITRIX_KP_ENTITY_TYPE_ID` с реальным entityTypeId в портале |
| КП создаётся без файла | Не найден файл на Диске/в UF | Проверить `BITRIX_SOURCE_FILE_FIELD` и warnings в meta предложения |
