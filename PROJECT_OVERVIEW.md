# Alpstein AI — обзор проекта

**Дата:** 7 июня 2026  
**Источник:** анализ репозитория (`specs/`, `backend/`, `n8n/`, `docs/project-status/`, `docs/ops/`)  
**Принцип:** описано только то, что подтверждается кодом, экспортами workflow и операционной документацией. Планируемое или частично включённое помечено явно.

---

## 1. Что это за продукт

**Alpstein AI** — мультитенантная платформа AI-ассистента для малого и среднего бизнеса (первый рынок — Швейцария). Продукт принимает входящие сообщения клиентов из мессенджеров и веб-чата, автоматически отвечает с помощью AI, сохраняет переписку и лиды, уведомляет владельца бизнеса и при необходимости копирует данные в CRM.

Ключевое позиционирование из спецификации: *«Never miss a customer message again»* — не пропускать обращения клиентов и снижать ручную нагрузку на владельца.

Продукт **не** является полноценной CRM, биллинговой SaaS-платформой или self-service порталом — это практический инструмент коммуникации и захвата лидов с архитектурным заделом под масштабирование.

---

## 2. Какую бизнес-проблему решает

| Проблема | Как решает Alpstein AI |
|----------|------------------------|
| Пропущенные сообщения в WhatsApp/Telegram/Direct | Автоматический приём и ответ 24/7 |
| Ручные однотипные ответы | AI-ассистент с контекстом бизнеса и базой знаний |
| Отсутствие структурированного учёта обращений | Клиенты, диалоги, сообщения и лиды в PostgreSQL |
| Владелец не видит срочные заявки | Уведомления в Telegram (новый лид, срочность, эскалация, сбой AI) |
| Разрозненные каналы | Единый нормализованный контракт входящих сообщений |
| Данные не попадают в CRM | Опциональная синхронизация лидов и истории в ERPNext через n8n |

Целевые клиенты: рестораны, барбершопы, салоны, локальные магазины и сервисные компании без выстроенного CRM-процесса.

---

## 3. Какие каналы подключены

Статус по фактической реализации в репозитории (не по roadmap):

| Канал | Статус | Примечание |
|-------|--------|------------|
| **Telegram** (клиентский бот) | **Работает в production** | Единый workflow `alpstein-customer-ingress`, cutover E1.9 завершён |
| **Website Chat** (виджет) | **Реализован** | MVP-виджет `website-widget/`; kill switch `ALPSTEIN_WEBSITE_CHAT_ENABLED` |
| **Test Webhook** | **Работает** | Регрессия и демо (`channel=test`) |
| **Instagram Direct** | **Реализован в коде и workflow** | Backend: Meta webhook + dispatch в n8n; outbound через `POST /api/v1/channels/instagram/send-message`; флаги по умолчанию **выключены** (`ALPSTEIN_INSTAGRAM_N8N_INGRESS_ENABLED`, `ALPSTEIN_INSTAGRAM_OUTBOUND_ENABLED`) |
| **WhatsApp Cloud API** | **Частично** | `GET/POST /webhooks/meta` — верификация и приём сырых событий; полный ingress через n8n **отложен** (deferred) |
| **Email, голос, мобильное приложение** | **Не в MVP** | Явно исключены в `specs/mvp/mvp-scope.md` |

Демо-бизнесы в dev seed: `demo_barbershop_001`, `alpstein_ai_demo_001`.

---

## 4. Как работает архитектура

### Высокоуровневая схема

```text
Клиент → Канал (Telegram / Website / Instagram / Test)
              ↓
         n8n (нормализация, маршрутизация, доставка ответа, уведомления, CRM-хвост)
              ↓
    Python Backend (валидация, бизнес-логика, AI, запись в БД)
              ↓
         PostgreSQL (источник истины)
              ↓
         n8n → ответ клиенту + уведомление владельцу + ERPNext (опционально)
```

### Разделение ответственности

| Слой | Ответственность | Чего не делает |
|------|-----------------|----------------|
| **n8n** | Webhook, нормализация провайдера, HTTP в backend, отправка ответа, Telegram owner notify, ERPNext sync | Бизнес-логика, AI, прямая запись в PostgreSQL |
| **Backend (FastAPI)** | Tenant/business resolution, клиенты, диалоги, сообщения, лиды, AI-оркестрация, PromptRun | Прямая работа с API мессенджеров (кроме Instagram outbound и Meta intake) |
| **PostgreSQL** | Персистентные данные, AI-конфигурация, аудит AI | — |
| **AI (OpenAI)** | Генерация ответа | Прямой доступ к БД и внешним API |

### Ключевые архитектурные решения

- **Нормализованный контракт** — все каналы приводятся к `POST /api/v1/webhook/message`; backend не зависит от сырых payload Telegram/Meta.
- **Мультитенантность** — изоляция по `tenant_id` и `business_id`.
- **Один flow = одно поведение бота** — таблица `flows`, привязка к диалогам.
- **PostgreSQL — единственный SoT** для бизнес-данных; ERPNext получает CRM-копию.

Домен: `https://alpstein-ai.ch`, n8n: `https://n8n.alpstein-ai.ch`, API: `https://api.alpstein-ai.ch` (по ops-документации).

---

## 5. Какие технологии используются

| Категория | Стек |
|-----------|------|
| Backend | Python, FastAPI, SQLAlchemy (async), Alembic, Pydantic |
| База данных | PostgreSQL 15 |
| Автоматизация | n8n 2.22.5 |
| AI | OpenAI (через `AiGatewayService`) |
| Observability | `prompt_runs` в PostgreSQL; Langfuse (опционально, по умолчанию выкл. в production) |
| CRM | ERPNext на `https://crm.alpstein-ai.ch` |
| Инфраструктура | Docker Compose, Nginx (HTTPS), Contabo VPS |
| Тестирование | pytest (сотни тестов в `backend/tests/`) |

---

## 6. Как AI-ассистент обрабатывает сообщения

Полный путь для **не-дубликата** входящего сообщения (`WebhookMessageService`):

1. **Валидация** токена (`X-Alpstein-Webhook-Token`) и нормализованного JSON.
2. **Резолв сущностей** — business → tenant, customer (get-or-create), conversation (reuse open/waiting или create).
3. **Сохранение входящего сообщения** с идемпотентностью по `external_message_id`.
4. **Детекция сигналов лида** — эвристики по ключевым словам (срочность, запрос человека).
5. **Создание/обновление лида** через `LeadService`.
6. **AI-оркестрация** (`AiReplyOrchestrationCoordinator` → `AiReplyOrchestrationService`):
   - `AiConfigurationService` — профиль бизнеса, AI-профиль, channel rules, platform templates;
   - `KnowledgeRetrievalService` — релевантные сниппеты из `tenant_knowledge_sources` (текстовый поиск, без векторов);
   - загрузка истории (10–20 последних сообщений);
   - `GreetingPolicyService` — приветствие (FIRST_CONTACT / FOLLOW_UP);
   - `ConversationIntentService` — **частично**: только для `alpstein_ai_demo_001`;
   - `PromptBuilderService` — сборка **8 секций** промпта (platform rules, business context, behavior, knowledge, channel rules, history, current message);
   - `AiGatewayService` — единственная точка HTTP к OpenAI;
   - `PromptRunService` — аудит каждого вызова (модель, токены, latency, ошибки);
   - `LangfuseTracingService` — опциональная трассировка.
7. **Fallback** при сбое AI — `AiReplyFallbackService` (tenant fallback → platform default, флаг handoff).
8. **Сохранение исходящего AI-сообщения** в `messages`.
9. **Ответ n8n** — `reply_to_customer`, флаги `lead_created`/`lead_updated`, `notify_owner`, объект `notification`.

Защита от дубликатов webhook: повторный `external_message_id` не запускает новый AI-вызов и не создаёт дублирующий лид.

Конфигурация AI **не захардкожена** — поведение задаётся через tenant/business profiles, knowledge sources и prompt templates.

---

## 7. Как создаются лиды и клиенты в CRM/ERP

### Внутри Alpstein AI (обязательный путь)

1. **Клиент** — `CustomerService.get_or_create_customer` по `business_id` + идентификатор (телефон и/или `external_customer_id`).
2. **Диалог** — reuse активного (`open`, `waiting_for_customer`, `waiting_for_owner`) или создание нового.
3. **Лид** — на первом входящем сообщении (не-дубликат): `LeadService.create_lead`; при активном лиде — `update_lead`. Дедупликация по tenant + business + customer + conversation + статусам `new`/`in_progress`/`contacted`.
4. **Уведомление** — `NotificationPolicyService` определяет тип (`new_lead`, `urgent_lead`, `human_handoff`, `ai_failure`).

### ERPNext (опциональная CRM-копия)

Реализовано в n8n workflow `alpstein-customer-ingress` (Phase F.2.1 / F.2.2 / F.2.3):

- **Kill switch:** `ALPSTEIN_ERPNEXT_LEAD_SYNC_ENABLED` (по умолчанию `false` в репозитории).
- **Порядок:** после успешного `POST Backend` — неблокирующий хвост в ERPNext.
- **Дедупликация лидов в ERPNext** — по структурированным полям (`mobile_no`, `email_id`, `alpstein_channel`, `alpstein_chat_id`, `alpstein_external_user_id`, `lead_name`).
- **Кастомные поля Lead** — `alpstein_channel`, `alpstein_business_id`, профили Telegram/Instagram, touch-атрибуция и др. (скрипт `scripts/erpnext/create_alpstein_lead_fields.py`).
- **История переписки (F.2.3)** — вкладка «История переписки» на форме Lead; синхронизация linked `Communication` rows из PostgreSQL; backfill для существующих Instagram/Telegram сообщений выполнен.

PostgreSQL остаётся **источником истины**; сбой ERPNext не блокирует ответ клиенту.

### Другие CRM

Интеграции с HubSpot, Bitrix24, Google Sheets, Pipedrive в коде **не реализованы** — только описаны как будущие направления в спецификациях.

---

## 8. Какие интеграции уже есть

| Интеграция | Назначение | Статус |
|------------|------------|--------|
| **Telegram Bot API** | Входящие сообщения клиентов + уведомления владельцу | Production (unified ingress) |
| **Website Chat widget** | Веб-виджет → n8n → backend | Реализован; включение через env |
| **OpenAI** | Генерация ответов | Реализован |
| **Langfuse** | Трассировка AI (dev/staging) | Реализован; production off by default |
| **ERPNext** | CRM-копия лидов + история Communication | Реализован в workflow; **требует включения оператором** |
| **Meta / Instagram** | Webhook intake, dispatch в n8n, outbound send | Реализован в backend + workflow; **флаги по умолчанию выкл.** |
| **Meta / WhatsApp** | Webhook verify + raw intake | Частично (`/webhooks/meta`); полный pipeline deferred |
| **Test webhook** | Демо и регрессия | Реализован |

Аутентификация n8n → backend: заголовок `X-Alpstein-Webhook-Token` / `N8N_BACKEND_API_TOKEN`.

---

## 9. Преимущества для бизнеса

- **Скорость ответа** — мгновенная реакция на типовые вопросы без ожидания владельца.
- **Доступность 24/7** — ассистент работает вне рабочих часов.
- **Сохранение лидов** — каждое обращение фиксируется в БД и опционально в CRM.
- **Меньше рутины** — снижение повторяющихся ответов о ценах, часах работы, записи.
- **Профессиональный имидж** — структурированные ответы в стиле бизнеса.
- **Контроль владельца** — уведомления о новых/срочных лидах и запросах на человека.
- **Масштабируемая основа** — мультитенантность, единый контракт каналов, аудит AI (`prompt_runs`).
- **Надёжность** — идемпотентность, retry/replay protection, rate limiting и anti-spam (реализованы, часть флагов ждёт staging-валидации).

Модель монетизации (из спецификации, **не реализована в коде**): подписка 49–199 CHF/мес.

---

## 10. Что уже реализовано

### Backend

- Health/readiness endpoints (`GET /api/v1/health`, `/health/ready`).
- Полный webhook pipeline: `POST /api/v1/webhook/message`.
- Модели и миграции Alembic (tenants, businesses, customers, conversations, messages, leads, AI config, prompt_runs, flows, message_traces, delivery_events, retry/dead-letter, rate limits, anti-spam, instagram outbound и др.).
- AI-стек: Configuration → Knowledge → PromptBuilder → Gateway → PromptRun → Orchestration + Fallback.
- Lead/notification wire-up с keyword heuristics.
- Observability API, adapter monitoring, ingress isolation, spam/rate-limit protection.
- Instagram: Meta webhook intake, n8n dispatch, outbound send API.
- Dev seed AI-конфигурации (`demo_barbershop_001`, `alpstein_ai_demo_001`).
- Обширный pytest-набор (547+ тестов по состоянию на май 2026).

### n8n

- Test webhook workflow (Gate 1/2 пройдены).
- Unified customer ingress `alpstein-customer-ingress` (Telegram + Website + Instagram branches).
- Owner Telegram notifications.
- ERPNext Lead sync + Communication history tail.
- Экспорты в `n8n/workflows/`, ops runbooks в `docs/ops/`.

### Инфраструктура

- Portable Docker Compose: `postgres` + `backend` + `n8n`.
- HTTPS, nginx reverse proxy, migrate-then-serve entrypoint.
- Документированный deployment contract (B2.0–B2.9).

### Демонстрационный сценарий MVP

```text
Сообщение клиента → AI-ответ → сохранение диалога → лид → уведомление владельцу в Telegram
```

Сценарий **подтверждён** для test webhook и Telegram ingress; Website Chat — с kill switch; Instagram — в коде, production smoke **требует уточнения** операторского статуса флагов.

---

## 11. Что можно улучшить дальше

Приоритеты из `docs/project-status/next-steps.md` и открытых задач:

| Направление | Описание |
|-------------|----------|
| **WhatsApp ingress** | Полный pipeline через n8n (сейчас только Meta webhook intake) |
| **Production-hardening** | Staging-валидация rate limit (E3.5) и anti-spam (E3.6); включение ERPNext sync после smoke |
| **Instagram / Telegram live smoke** | Подтверждение end-to-end с включёнными флагами и ERPNext Communication sync без backfill |
| **Langfuse на compose backend** | Полная observability в production-like среде |
| **Self-service onboarding** | Нет UI для самостоятельной настройки бизнеса (вне MVP) |
| **Dashboard** | Нет фронтенд-панели для владельца (вне MVP) |
| **Биллинг / Stripe** | Не реализован |
| **Дополнительные CRM** | HubSpot, Bitrix24, Google Sheets — только в спецификациях |
| **Intent policy для всех tenant** | Сейчас расширенное поведение intent только для `alpstein_ai_demo_001` |
| **Attribution persistence (ATTR-3)** | Поля `source`/`attribution` валидируются, но не персистятся |
| **Автоматизация релизов (E4)** | Спроектирована, не реализована |
| **Vector RAG / embeddings** | Явно вне MVP |

---

## Ограничения и пометки «требует уточнения»

- **Актуальный production runtime** для каждого канала зависит от env-флагов и импорта workflow на сервере — в репозитории задокументированы значения по умолчанию (многие интеграции **выключены**).
- **WhatsApp** как клиентский канал — не закрыт end-to-end.
- **Модель подписки и цены** — бизнес-план, не код.
- **Количество реальных pilot-клиентов** — требует уточнения у владельца продукта (в коде есть demo tenant/business).
- Документ `docs/architecture/canonical-runtime-architecture.md` датирован 2026-05-27; часть каналов (Instagram, ERPNext F.2.3) развивалась позже — при расхождении приоритет у кода и `current-state.md`.

---

*Документ подготовлен для презентации и коммерческого предложения. Техническая детализация: `specs/`, `docs/project-status/`, `AGENTS.md`.*
