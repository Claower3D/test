# OLX Partner API — автоматизация кабинета (HUB MASTER)

Готовый каркас дневного пайплайна поверх **OLX Kazakhstan Partner API** (OpenAPI v2).

## Функции
1. Сбор статистики объявлений (`advert_views`, `phone_views`, `users_observing`).
2. Оптимизация неэффективных (правила -> `PUT /adverts/{id}`).
3. Автоподнятие (`POST /adverts/{id}/paid-features`) — с **бюджет-лимитом**.
4. Лиды из чата (`/threads`) -> CRM.
5. CPL = расход / (`phone_views` + чат-лиды).
6. Lifecycle: deactivate -> delete, по правилам.
7. История по дням в SQLite (сверка с Google-таблицей).

## ❗ Твои шаги перед запуском (по правилам делаешь сам)
1. На developer.olx.kz заполнить Partner details (Company, БИН, Website, Services) + принять Terms.
2. Создать приложение -> получить `client_id` и `client_secret`.
3. Указать Redirect URI (напр. http://localhost:8000/callback).
4. Вписать ключи в `.env`.
5. `python run.py auth` -> авторизовать аккаунт в браузере (OAuth — твоё действие).

## Запуск
```bash
pip install -r requirements.txt
cp .env.example .env        # вписать client_id/secret
python run.py auth          # разовая OAuth-авторизация
python run.py collect       # собрать статистику/чаты/расход -> olx.db
python run.py cpl           # отчёт CPL
python run.py rules         # кандидаты на оптимизацию + план поднятия (DRY-RUN)
python run.py daily         # полный прогон
```
Боевое автоподнятие включается только явно: `rules.promote(apply=True)` и в рамках `PROMO_DAILY_BUDGET_KZT`.

## Соответствие правилам OLX
- Только официальный Partner API, **без скрапинга**.
- Бюджет-предохранитель на поднятия (деньги не утекут).
- Идемпотентность через `external_id`.
- Удаление двухшаговое (deactivate -> delete).
- Ретраи и паузы на `429`.

## Multi-account
Каждый аккаунт авторизуется отдельно: `python run.py auth <account>` и далее `... collect <account>`.
Токены хранятся в `tokens.json` по метке аккаунта.

---

# 🚀 Деплой на Railway (GitHub → Railway)

## 1. Репозиторий
Залей все эти файлы в новый GitHub-репозиторий (как делал с другими ботами).

## 2. Railway: создать сервис
New Project → **Deploy from GitHub repo** → выбери репозиторий. Railway сам соберёт (есть `railway.json` + `Procfile`).

## 3. Volume для персистентности
Добавь **Volume** и смонтируй на путь `/data` (там хранятся токены и база истории, чтобы не терялись при рестарте).

## 4. Переменные (Variables)
```
OLX_CLIENT_ID=200470
OLX_CLIENT_SECRET=<секрет из «Ваши заявки» ❱❱>
DATA_DIR=/data
TZ=Asia/Almaty
DAILY_HOUR=6
PROMO_DAILY_BUDGET_KZT=5000
```
> Секрет вписывается ТОЛЬКО сюда, в Railway. Не в код, не в файл.

## 5. Домен и Redirect URI
- В Railway: Settings → Networking → **Generate Domain**. Получишь адрес вида `https://olx-bot-production.up.railway.app`.
- Добавь переменную: `OLX_REDIRECT_URI=https://<этот-домен>/olx/callback`
- На **developer.olx.kz** в приложении пропиши тот же Redirect URI: `https://<этот-домен>/olx/callback` (https, WAF пропустит).
- Перезапусти сервис (Redeploy).

## 6. Авторизация аккаунтов (мульти-аккаунт)
Открой `https://<домен>/` — это панель бота. Для **каждого** OLX-аккаунта:
1. Залогинься в OLX под этим аккаунтом в том же браузере.
2. На панели впиши метку (напр. `account_2`) → «Авторизовать в OLX».
3. Подтверди доступ → аккаунт появится в списке «Подключённые».
Повтори для всех аккаунтов. Это разово — дальше всё на refresh-токенах.

## 7. Готово
- Планировщик сам гоняет сбор каждый день в `DAILY_HOUR`.
- Кнопка «Запустить сбор сейчас» — ручной прогон.
- `/status` — JSON со списком подключённых аккаунтов.
