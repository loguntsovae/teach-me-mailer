# 🧪 План тестирования Teach Me Mailer

## Обзор

Комплексный план тестирования для покрытия всего функционала проекта с целью достижения 100% покрытия кода и добавления бейджа в README.

---

## 📊 Структура тестов

```
tests/
├── __init__.py
├── conftest.py                    # Фикстуры и общие настройки
│
├── unit/                          # Юнит-тесты (изолированные компоненты)
│   ├── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── test_auth.py          # Тесты аутентификации
│   │   ├── test_mailer.py        # Тесты отправки email
│   │   ├── test_rate_limit.py    # Тесты лимитов (in-memory)
│   │   ├── test_atomic_rate_limit.py  # Тесты атомарных лимитов
│   │   ├── test_usage_tracking.py     # Тесты трекинга использования
│   │   ├── test_domain_validation.py  # Тесты валидации доменов
│   │   └── test_email_queue.py        # Тесты очереди email
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── test_api_key.py       # Тесты модели APIKey
│   │   ├── test_daily_usage.py   # Тесты модели DailyUsage
│   │   └── test_send_log.py      # Тесты модели SendLog
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── test_mail.py          # Тесты Pydantic схем
│   │
│   └── core/
│       ├── __init__.py
│       ├── test_config.py        # Тесты конфигурации
│       └── test_deps.py          # Тесты зависимостей
│
├── integration/                   # Интеграционные тесты
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── test_mail_endpoint.py     # Тесты /api/v1/send
│   │   ├── test_health_endpoint.py   # Тесты /health
│   │   ├── test_usage_endpoint.py    # Тесты /api/v1/usage
│   │   └── test_admin_endpoints.py   # Тесты admin UI
│   │
│   ├── test_database.py          # Тесты работы с БД
│   ├── test_rate_limiting.py     # Интеграционные тесты лимитов
│   ├── test_email_flow.py        # End-to-end отправка email
│   └── test_auth_flow.py         # Интеграционные тесты аутентификации
│
└── e2e/                          # End-to-end тесты
    ├── __init__.py
    ├── test_complete_flow.py     # Полный цикл: создание ключа → отправка
    ├── test_monitoring.py        # Тесты метрик Prometheus
    └── test_error_handling.py    # Тесты обработки ошибок
```

---

## 🎯 1. Юнит-тесты (Unit Tests)

### 1.1 Services Layer

#### `test_auth.py` - Сервис аутентификации
**Цели:**
- Валидация хеширования API ключей (bcrypt)
- Проверка верификации ключей
- Тесты на разные статусы (VALID, INVALID, INACTIVE)
- Генерация новых API ключей с корректными префиксами

**Тест-кейсы:**
```python
- test_hash_api_key()                    # Хеширование ключа
- test_verify_api_key_valid()            # Верификация валидного ключа
- test_verify_api_key_invalid()          # Верификация невалидного ключа
- test_validate_active_key()             # Проверка активного ключа
- test_validate_inactive_key()           # Проверка неактивного ключа
- test_validate_nonexistent_key()        # Проверка несуществующего ключа
- test_generate_api_key()                # Генерация нового ключа
- test_create_api_key_with_limits()      # Создание ключа с лимитами
- test_key_prefix_validation()           # Проверка префикса sk_
```

#### `test_mailer.py` - Сервис отправки email
**Цели:**
- Отправка email через SMTP (мокирование aiosmtplib)
- Валидация email адресов
- Обработка ошибок SMTP
- Проверка domain allowlist

**Тест-кейсы:**
```python
- test_send_email_success()              # Успешная отправка
- test_send_email_html_only()            # Отправка HTML
- test_send_email_text_only()            # Отправка text
- test_send_email_both_formats()         # HTML + text
- test_send_email_invalid_recipient()    # Невалидный recipient
- test_send_email_smtp_error()           # Ошибка SMTP
- test_send_email_connection_timeout()   # Таймаут подключения
- test_domain_allowlist_allowed()        # Разрешенный домен
- test_domain_allowlist_blocked()        # Заблокированный домен
- test_custom_headers()                  # Кастомные заголовки
- test_message_id_generation()           # Генерация message-id
```

#### `test_rate_limit.py` - In-memory rate limiting
**Цели:**
- Проверка лимитов в памяти
- Очистка старых запросов
- Учет временных окон

**Тест-кейсы:**
```python
- test_within_daily_limit()              # В пределах лимита
- test_exceed_daily_limit()              # Превышение лимита
- test_cleanup_old_requests()            # Очистка старых запросов
- test_multiple_api_keys()               # Разные ключи независимо
- test_rate_window_days()                # Проверка временного окна
- test_concurrent_requests()             # Параллельные запросы
```

#### `test_atomic_rate_limit.py` - Атомарное rate limiting (PostgreSQL)
**Цели:**
- Атомарные операции с БД
- Проверка race conditions
- Транзакционная целостность

**Тест-кейсы:**
```python
- test_atomic_check_and_increment()      # Атомарная проверка+инкремент
- test_concurrent_updates()              # Конкурентные обновления
- test_daily_limit_reset()               # Сброс дневного лимита
- test_api_key_custom_limits()           # Кастомные лимиты ключа
- test_transaction_rollback()            # Откат транзакций
```

#### `test_usage_tracking.py` - Трекинг использования
**Цели:**
- Запись статистики отправки
- Агрегация данных по дням
- Получение usage для API ключа

**Тест-кейсы:**
```python
- test_track_email_sent()                # Запись отправки
- test_get_daily_usage()                 # Получение дневной статистики
- test_get_usage_history()               # История использования
- test_calculate_totals()                # Подсчет итогов
```

#### `test_domain_validation.py` - Валидация доменов
**Цели:**
- Проверка email адресов
- Валидация доменов из allowlist

**Тест-кейсы:**
```python
- test_validate_email_format()           # Формат email
- test_validate_domain_allowed()         # Разрешенный домен
- test_validate_domain_blocked()         # Заблокированный домен
- test_extract_domain_from_email()       # Извлечение домена
```

#### `test_email_queue.py` - Очередь email
**Цели:**
- Добавление email в очередь
- Обработка background tasks

**Тест-кейсы:**
```python
- test_queue_email()                     # Добавление в очередь
- test_process_queue()                   # Обработка очереди
- test_queue_error_handling()            # Обработка ошибок
```

### 1.2 Models Layer

#### `test_api_key.py` - Модель APIKey
**Тест-кейсы:**
```python
- test_create_api_key()                  # Создание ключа
- test_api_key_fields()                  # Проверка полей
- test_api_key_relationships()           # Связи с другими моделями
- test_allowed_recipients_field()        # Поле allowed_recipients
```

#### `test_daily_usage.py` - Модель DailyUsage
**Тест-кейсы:**
```python
- test_create_daily_usage()              # Создание записи
- test_increment_usage()                 # Инкремент счетчика
- test_unique_constraint()               # Уникальность api_key + date
```

#### `test_send_log.py` - Модель SendLog
**Тест-кейсы:**
```python
- test_create_send_log()                 # Создание лога
- test_log_fields()                      # Проверка полей
- test_status_tracking()                 # Статусы отправки
```

### 1.3 Schemas Layer

#### `test_mail.py` - Pydantic схемы
**Тест-кейсы:**
```python
- test_mail_request_validation()         # Валидация MailRequest
- test_email_format_validation()         # Проверка формата email
- test_subject_validation()              # Проверка subject
- test_body_validation()                 # Проверка body (html/text)
- test_mail_response_serialization()     # Сериализация MailResponse
```

### 1.4 Core Layer

#### `test_config.py` - Конфигурация
**Тест-кейсы:**
```python
- test_load_settings_from_env()          # Загрузка из .env
- test_default_settings()                # Дефолтные значения
- test_smtp_settings()                   # SMTP конфигурация
- test_database_url()                    # Database URL
- test_rate_limit_settings()             # Настройки лимитов
```

#### `test_deps.py` - Зависимости FastAPI
**Тест-кейсы:**
```python
- test_get_db_dependency()               # Получение DB сессии
- test_get_current_api_key()             # Получение API ключа
- test_get_settings_dependency()         # Получение настроек
- test_dependency_injection()            # Инъекция зависимостей
```

---

## 🔗 2. Интеграционные тесты (Integration Tests)

### 2.1 API Endpoints

#### `test_mail_endpoint.py` - POST /api/v1/send
**Тест-кейсы:**
```python
- test_send_email_success()              # Успешная отправка
- test_send_email_unauthorized()         # Без API ключа
- test_send_email_invalid_key()          # Невалидный ключ
- test_send_email_rate_limit()           # Превышение лимита
- test_send_email_invalid_data()         # Невалидные данные
- test_send_email_allowed_recipients()   # Проверка allowed_recipients
- test_send_email_background_task()      # Background обработка
- test_concurrent_requests()             # Параллельные запросы
```

#### `test_health_endpoint.py` - GET /health
**Тест-кейсы:**
```python
- test_health_check_ok()                 # Статус OK
- test_health_check_db_connection()      # Проверка БД
- test_health_check_smtp_connection()    # Проверка SMTP
```

#### `test_usage_endpoint.py` - GET /api/v1/usage
**Тест-кейсы:**
```python
- test_get_usage_authorized()            # Получение usage
- test_get_usage_unauthorized()          # Без авторизации
- test_usage_statistics()                # Статистика
```

#### `test_admin_endpoints.py` - Admin UI
**Тест-кейсы:**
```python
- test_admin_list_keys()                 # Список ключей
- test_admin_create_key()                # Создание ключа
- test_admin_page_render()               # Рендер HTML страниц
```

### 2.2 Database Integration

#### `test_database.py`
**Тест-кейсы:**
```python
- test_connection_pool()                 # Connection pooling
- test_transaction_commit()              # Коммит транзакций
- test_transaction_rollback()            # Откат транзакций
- test_concurrent_writes()               # Конкурентная запись
- test_migrations()                      # Миграции Alembic
```

### 2.3 Rate Limiting Flow

#### `test_rate_limiting.py`
**Тест-кейсы:**
```python
- test_rate_limit_enforcement()          # Применение лимитов
- test_rate_limit_per_key()              # Лимиты по ключу
- test_rate_limit_window()               # Временное окно
- test_rate_limit_reset()                # Сброс лимитов
```

### 2.4 Email Flow

#### `test_email_flow.py`
**Тест-кейсы:**
```python
- test_complete_email_flow()             # Полный цикл отправки
- test_email_retry_logic()               # Логика повторов
- test_email_failure_handling()          # Обработка ошибок
```

### 2.5 Authentication Flow

#### `test_auth_flow.py`
**Тест-кейсы:**
```python
- test_api_key_authentication()          # Аутентификация
- test_invalid_key_rejection()           # Отклонение невалидных ключей
- test_inactive_key_rejection()          # Отклонение неактивных ключей
```

---

## 🎭 3. End-to-End тесты (E2E Tests)

#### `test_complete_flow.py`
**Тест-кейсы:**
```python
- test_full_lifecycle()                  # Создание ключа → отправка → проверка
- test_multi_user_scenario()             # Множество пользователей
- test_high_load_scenario()              # Высокая нагрузка
```

#### `test_monitoring.py`
**Тест-кейсы:**
```python
- test_prometheus_metrics()              # Метрики Prometheus
- test_sentry_error_tracking()           # Отслеживание ошибок Sentry
- test_structured_logging()              # Структурированные логи
```

#### `test_error_handling.py`
**Тест-кейсы:**
```python
- test_database_connection_failure()     # Отказ БД
- test_smtp_connection_failure()         # Отказ SMTP
- test_invalid_configuration()           # Невалидная конфигурация
- test_graceful_degradation()            # Деградация сервиса
```

---

## 🛠️ 4. Инфраструктура тестирования

### 4.1 Фикстуры (`conftest.py`)

```python
@pytest.fixture
async def db_session():
    """Тестовая БД сессия с откатом после теста"""

@pytest.fixture
async def test_client():
    """HTTP клиент для API тестов"""

@pytest.fixture
async def test_api_key():
    """Тестовый API ключ"""

@pytest.fixture
def mock_smtp():
    """Мок SMTP сервера"""

@pytest.fixture
def settings():
    """Тестовые настройки"""

@pytest.fixture
async def clean_database():
    """Очистка БД перед тестом"""
```

### 4.2 Моки и стабы

```python
# Мокирование внешних зависимостей:
- aiosmtplib.SMTP           # SMTP клиент
- sentry_sdk                # Sentry
- prometheus metrics        # Метрики
```

### 4.3 Тестовые данные

```python
# Фабрики для генерации тестовых данных:
- APIKeyFactory
- EmailFactory
- UsageFactory
```

---

## 📈 5. Метрики покрытия

### Целевые показатели:
- **Общее покрытие:** ≥ 95%
- **Unit tests:** ≥ 98%
- **Integration tests:** ≥ 90%
- **E2E tests:** Критические пути 100%

### Области, требующие особого внимания:
1. **Rate limiting** - критическая бизнес-логика
2. **Authentication** - безопасность
3. **Email sending** - основной функционал
4. **Error handling** - надежность

---

## 🚀 6. Настройка CI/CD

### GitHub Actions Workflow (`.github/workflows/test.yml`)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.14'
      - name: Install dependencies
        run: |
          pip install -e ".[test]"
      - name: Run tests
        run: |
          pytest --cov=app --cov-report=xml --cov-report=html
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage.xml
```

---

## 🏅 7. Бейджи для README

После настройки CI/CD добавить в `README.md`:

```markdown
[![Tests](https://github.com/loguntsovae/teach-me-mailer/workflows/Tests/badge.svg)](https://github.com/loguntsovae/teach-me-mailer/actions?query=workflow%3ATests)
[![Coverage](https://codecov.io/gh/loguntsovae/teach-me-mailer/branch/main/graph/badge.svg)](https://codecov.io/gh/loguntsovae/teach-me-mailer)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
```

---

## 📝 8. Порядок реализации

### Фаза 1: Подготовка (1-2 дня) ✅ ЗАВЕРШЕНА
1. ✅ Создать структуру директорий `tests/`
2. ✅ Настроить `conftest.py` с базовыми фикстурами
3. ✅ Настроить тестовую БД (PostgreSQL на localhost)
4. ✅ Добавить pytest плагины в pyproject.toml
5. ✅ Создать .env.test для тестовой конфигурации
6. ✅ Создать pytest.ini с настройками
7. ✅ Smoke тесты проходят успешно

### Фаза 2: Юнит-тесты (3-4 дня)
1. ✅ Тесты для services (auth, mailer, rate_limit)
2. ✅ Тесты для models
3. ✅ Тесты для schemas
4. ✅ Тесты для core

### Фаза 3: Интеграционные тесты (2-3 дня)
1. ✅ API endpoints тесты
2. ✅ Database интеграция
3. ✅ Rate limiting flows
4. ✅ Email flows

### Фаза 4: E2E тесты (1-2 дня)
1. ✅ Complete flows
2. ✅ Monitoring
3. ✅ Error handling

### Фаза 5: CI/CD (1 день)
1. ✅ Настроить GitHub Actions
2. ✅ Интегрировать Codecov
3. ✅ Добавить бейджи в README

### Фаза 6: Оптимизация (1 день)
1. ✅ Достичь 95%+ покрытия
2. ✅ Оптимизировать медленные тесты
3. ✅ Документировать тест-кейсы

---

## 🔍 9. Инструменты и библиотеки

```toml
[dependency-groups]
test = [
    "pytest>=7.4.0",              # Тестовый фреймворк
    "pytest-asyncio>=0.21.0",     # Async тесты
    "pytest-cov>=4.1.0",          # Покрытие кода
    "pytest-mock>=3.12.0",        # Моки
    "httpx>=0.25.0",              # HTTP клиент для API тестов
    "faker>=20.1.0",              # Генерация тестовых данных
    "aiosqlite>=0.19.0",          # Async SQLite для тестов
    "pytest-xdist>=3.5.0",        # Параллельный запуск тестов
    "pytest-timeout>=2.2.0",      # Таймауты для тестов
]
```

---

## 📊 10. Отчетность

### Генерация отчетов:

```bash
# HTML отчет
pytest --cov=app --cov-report=html

# Terminal отчет с пропущенными строками
pytest --cov=app --cov-report=term-missing

# XML для CI/CD
pytest --cov=app --cov-report=xml
```

### Анализ покрытия:

```bash
# Открыть HTML отчет
open htmlcov/index.html

# Проверить конкретный модуль
pytest --cov=app.services.auth --cov-report=term-missing
```

---

## ✅ Чек-лист перед релизом

- [ ] Все тесты проходят успешно
- [ ] Покрытие кода ≥ 95%
- [ ] CI/CD настроен и работает
- [ ] Бейджи добавлены в README
- [ ] Документация тестов обновлена
- [ ] Нет пропущенных edge cases
- [ ] Перформанс тестов приемлемый (<5 минут на полный прогон)
- [ ] Все критические пути покрыты E2E тестами

---

## 🎯 Итоговая цель

**Достичь 95%+ покрытия кода тестами, обеспечить надежность и качество продукта, добавить видимые бейджи качества в README для демонстрации на GitHub.**
