# Telegram Chat Parser Bot

Production-ready Telegram бот для парсинга чатов по ключевым словам с встроенной админ-панелью.

## 🚀 Стек технологий

- **Python 3.11+**
- **Aiogram 3** - Telegram Bot Framework (Long Polling)
- **SQLAlchemy 2.0 + Alembic** - ORM + миграции (SQLite → PostgreSQL ready)
- **Redis** - FSM storage + L2 Cache
- **Pydantic v2** - валидация конфигурации
- **Loguru** - кастомное логирование (DEBUG, INFO, WARNING, ERROR)
- **aiosqlite** - асинхронная работа с SQLite

## 📁 Структура проекта

```
crypto-algos-bot/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Точка входа
│   ├── config.py               # Настройки через pydantic-settings
│   ├── core/
│   │   ├── __init__.py
│   │   ├── cache.py            # L1 (memory) + L2 (Redis) cache
│   │   └── logging_config.py   # Loguru конфигурация
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy модели
│   │   └── engine.py           # Настройка БД
│   ├── fsm/
│   │   ├── __init__.py
│   │   └── states.py           # FSM состояния
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py            # /start handler
│   │   └── admin.py            # Админ панель
│   ├── keyboards/
│   │   ├── __init__.py
│   │   └── inline.py           # Inline клавиатуры
│   ├── middlewares/
│   │   ├── __init__.py
│   │   └── logging.py          # Логирование запросов
│   ├── services/
│   │   ├── __init__.py
│   │   ├── parser.py           # Логика парсинга чатов
│   │   ├── admin_service.py    # Бизнес-логика админки
│   │   └── notification.py     # Уведомления
│   └── utils/
│       └── __init__.py
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial.py
├── .env.example
├── .gitignore
├── alembic.ini
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 📦 Установка

### 1. Клонировать репозиторий

```bash
git clone <repository-url>
cd crypto-algos-bot
```

### 2. Создать виртуальное окружение

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Настроить .env

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
# Bot Token (получить у @BotFather)
BOT_TOKEN=your_bot_token_here

# Redis URL
REDIS_URL=redis://localhost:6379/0

# Database URL (SQLite по умолчанию)
DATABASE_URL=sqlite+aiosqlite:///./data/bot.db

# Для PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bot_db

# Админ панель (ID администратора, можно несколько через запятую)
ADMIN_IDS=123456789

# Логирование
LOG_LEVEL=DEBUG
LOG_FILE=logs/bot.log

# Парсинг
PARSING_LIMIT=100
CACHE_TTL_L1=300
CACHE_TTL_L2=600
```

### 5. Применить миграции

```bash
alembic upgrade head
```

### 6. Запустить бота

```bash
python -m app.main
```

## 🐳 Docker

### Запуск с Docker Compose

```bash
docker-compose up -d
```

Это запустит:
- **Redis** на порту 6379
- **Bot** с подключением к Redis

### Просмотр логов

```bash
docker-compose logs -f bot
```

### Остановка

```bash
docker-compose down
```

## 🎯 Функционал

### Парсинг чатов
- Мониторинг указанных чатов по ключевым словам
- Двухуровневое кеширование (L1 - память, L2 - Redis)
- Фильтрация дубликатов
- Автоматическое сохранение в БД

### Админ-панель (полностью inline, edit_message_text)

**💬 Чаты:**
- Добавить чат в мониторинг
- Удалить чат
- Просмотр списка

**🔑 Ключевые слова:**
- Добавить слово для отслеживания
- Удалить слово
- Просмотр списка

**📨 Сообщения:**
- Просмотр найденных сообщений
- Детали: группа, отправитель, текст, ключевые слова
- Ссылка на оригинальное сообщение
- Пагинация

**⚙️ Настройки:**
- Статистика
- Очистка кеша

### Уведомления
При нахождении совпадения админ получает уведомление:
- Название группы
- ID отправителя
- Текст сообщения
- Ключевые слова
- Ссылка на чат с сообщением

## 🔑 Команды

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/admin` | Вход в админ-панель (только для админов) |

## 🏗 Архитектура

### Кеширование (L1 + L2)

```
┌─────────────────┐
│   Запрос кеша   │
└────────┬────────┘
         │
    ┌────▼────┐
    │  L1     │ ← In-memory (dict, LRU)
    │  Cache  │ ← TTL: 5 минут
    └────┬────┘
         │ Miss
    ┌────▼────┐
    │  L2     │ ← Redis
    │  Cache  │ ← TTL: 10 минут
    └─────────┘
```

**Преимущества:**
- ⚡ Мгновенный доступ к L1
- 🔄 Распределённый L2 для рестартов
- 📉 Меньше запросов к Telegram API
- 💾 Меньше нагрузки на БД

### Переход на PostgreSQL

В `.env` просто измените:

```env
# Было (SQLite)
DATABASE_URL=sqlite+aiosqlite:///./data/bot.db

# Стало (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bot_db
```

И примените миграции:

```bash
alembic upgrade head
```

Alembic автоматически создаст все таблицы.

## 📝 Логирование

Логи с уровнями: **DEBUG**, **INFO**, **WARNING**, **ERROR**

**Расположение:**
- Консоль (цветной вывод)
- Файл: `logs/bot.log`
- Ротация: 50MB
- Хранение: 30 дней

**Пример логов:**
```
2026-04-13 10:30:45 | INFO     | handlers.start:cmd_start:15 | Пользователь запустил бота | User: Иван | ID: 123456789
2026-04-13 10:30:46 | DEBUG    | core.cache:get:45 | L1 Cache hit | Key: chat:123456
2026-04-13 10:30:47 | INFO     | services.parser:check_message:35 | Найдено совпадение | Chat: Crypto Chat | Keywords: bitcoin, btc
```

## 🔄 Alembic миграции

**Создать новую миграцию:**
```bash
alembic revision --autogenerate -m "description"
```

**Применить миграции:**
```bash
alembic upgrade head
```

**Откатить миграцию:**
```bash
alembic downgrade -1
```

**Проверить статус:**
```bash
alembic current
```

## 🛡 Безопасность

- ✅ Токен бота в `.env` (не в коде)
- ✅ Admin IDs через переменную окружения
- ✅ Middleware для логирования всех запросов
- ✅ Валидация входных данных через Pydantic
- ✅ Кеширование для снижения нагрузки на API

## 📊 База данных

### Мониторинг чатов (`monitored_chats`)
| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer | Primary Key |
| chat_id | BigInteger | ID чата (unique) |
| chat_title | String | Название чата |
| chat_username | String | Username чата |
| is_active | Boolean | Активен ли |
| created_at | DateTime | Дата создания |

### Ключевые слова (`keywords`)
| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer | Primary Key |
| word | String | Ключевое слово (unique) |
| is_active | Boolean | Активно ли |
| created_at | DateTime | Дата создания |

### Парсенные сообщения (`parsed_messages`)
| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer | Primary Key |
| message_id | BigInteger | ID сообщения |
| chat_id | BigInteger | ID чата |
| chat_title | String | Название чата |
| user_id | BigInteger | ID отправителя |
| username | String | Username отправителя |
| text | Text | Текст сообщения |
| matched_keywords | String | Найденные ключевые слова |
| message_link | String | Ссылка на сообщение |
| parsed_at | DateTime | Время парсинга |
| is_sent | Boolean | Отправлено ли уведомление |

## 👨‍💻 Разработка

### Добавить новый обработчик

1. Создайте файл в `app/handlers/`
2. Импортируйте роутер в `app/main.py`
3. Добавьте логирование через `get_logger`

### Добавить новую клавиатуру

1. Добавьте функцию в `app/keyboards/inline.py`
2. Используйте `InlineKeyboardBuilder`
3. Всегда добавляйте кнопку "Назад"

### Добавить новый сервис

1. Создайте класс в `app/services/`
2. Используйте логирование на всех методах
3. Кешируйте через `cache_manager`

## 🐛 Troubleshooting

### Бот не запускается
- Проверьте `.env` файл
- Убедитесь что Redis запущен
- Проверьте логи: `logs/bot.log`

### Redis не подключается
```bash
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

### Ошибка миграций
```bash
alembic stamp head  # Отметить как применённую
alembic upgrade head  # Применить
```

## 📝 TODO

- [ ] Фоновый парсинг чатов по расписанию
- [ ] Экспорт данных в CSV/JSON
- [ ] Фильтры по датам
- [ ] Статистика и графики
- [ ] Мультиязычность
- [ ] Webhook режим

## 👨‍💻 Автор

Разработано с ❤️ для портфолио

**Стек:** Aiogram 3 + SQLAlchemy + Redis + Pydantic + Loguru

## 📄 Лицензия

MIT
