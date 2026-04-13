# Telegram Chat Parser Bot

Production-ready Telegram бот для парсинга чатов по ключевым словам с встроенной админ-панелью.

**Userbot на Pyrogram** — реальный парсинг сообщений из групп и каналов через MTProto протокол.

## 🚀 Стек технологий

- **Python 3.11+**
- **Aiogram 3** - Telegram Bot Framework (Long Polling)
- **Pyrogram 2.0** - Userbot (MTProto) для чтения сообщений
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
│   │   ├── admin.py            # Админ панель
│   │   └── userbot_handler.py  # Авторизация userbot
│   ├── keyboards/
│   │   ├── __init__.py
│   │   └── inline.py           # Inline клавиатуры
│   ├── middlewares/
│   │   ├── __init__.py
│   │   ├── logging.py          # Логирование запросов
│   │   └── database.py         # Сессия БД
│   ├── services/
│   │   ├── __init__.py
│   │   ├── userbot.py          # Pyrogram userbot сервис
│   │   ├── parser.py           # Логика парсинга
│   │   ├── admin_service.py    # Бизнес-логика админки
│   │   ├── notification.py     # Уведомления
│   │   ├── chat_monitor.py     # Фоновый мониторинг (fallback)
│   ├── └── __init__.py
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

### 4. Получить API ID/Hash для Userbot

1. Зайдите на **[my.telegram.org](https://my.telegram.org)**
2. Войдите с номером телефона
3. Перейдите в **API development tools**
4. Создайте приложение (App title, description — любые)
5. Скопируйте **App api_id** и **App api_hash**

### 5. Настроить .env

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

# Админ панель (ID администратора, можно несколько через запятую)
ADMIN_IDS=123456789

# Логирование
LOG_LEVEL=DEBUG
LOG_FILE=logs/bot.log

# Парсинг
PARSING_LIMIT=100
CACHE_TTL_L1=300
CACHE_TTL_L2=600
MONITORING_INTERVAL=10

# Pyrogram Userbot (получить на https://my.telegram.org/apps)
API_ID=12345678
API_HASH=your_api_hash_here
USERBOT_SESSION=userbot.session
```

### 6. Применить миграции

```bash
alembic upgrade head
```

### 7. Запустить бота

```bash
python -m app.main
```

При первом запуске Userbot попросит:
1. **Номер телефона** — введите `+7XXXXXXXXXX`
2. **Код подтверждения** — придёт в Telegram
3. **2FA пароль** — если включена двухфакторная аутентификация

После авторизации session сохранится в `userbot.session`.

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

### Userbot парсинг (Pyrogram)
- **Реальное чтение сообщений** из групп и каналов
- Поддержка **MTProto** протокола
- Автоматическая проверка **ключевых слов**
- Кеширование обработанных сообщений
- Отправка уведомлений админам

### Двухуровневое кеширование

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
    │  L2     │ ← Redis (JSON сериализация)
    │  Cache  │ ← TTL: 10 минут
    └─────────┘
```

**Преимущества:**
- ⚡ Мгновенный доступ к L1
- 🔄 Распределённый L2 для рестартов
- 📉 Меньше нагрузки на БД
- 🧹 Автоматическая очистка по TTL

### Админ-панель (полностью inline, edit_message_text)

**💬 Чаты:**
- Добавить чат (ID, @username, ссылка)
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
- Статус Userbot
- Очистка кеша
- Управление мониторингом

### Уведомления
При нахождении совпадения админ получает:
- 📝 Название группы
- 👤 ID отправителя
- 🔑 Ключевые слова
- 💬 Текст сообщения
- 🔗 Ссылка на чат

## 🔑 Команды

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/admin` | Вход в админ-панель (только для админов) |

## 🏗 Архитектура

### Чистая архитектура

```
Handlers → Services → Database
   ↓          ↓          ↓
Keyboards  Cache      Models
   ↓          ↓          ↓
Middleware FSM        Engine
```

### Поток данных

```
1. Userbot читает сообщения (Pyrogram)
2. Проверяет monitored_chats
3. Проверяет ключевые слова
4. Сохраняет в БД (SQLAlchemy)
5. Кеширует (L1 + L2)
6. Отправляет уведомление админу (Aiogram)
```

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
2026-04-13 21:38:23 | INFO | Userbot запущен | User: Mulenrush (@mulenrudsh)
2026-04-13 21:38:23 | INFO | Загружено 2 чатов для мониторинга
2026-04-13 21:39:05 | DEBUG | Прочитано сообщение | Chat: Бизнес | Msg ID: 12345
2026-04-13 21:39:05 | INFO | Найдено совпадение | Keywords: крипта, биткоин
2026-04-13 21:39:06 | INFO | Сообщение сохранено | ID: 1
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
- ✅ API ID/Hash через переменные окружения
- ✅ Admin IDs через переменную окружения
- ✅ `userbot.session` в `.gitignore`
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

### Userbot не авторизуется
- Проверьте API ID/Hash на my.telegram.org
- Убедитесь что номер телефона верный
- Удалите `userbot.session` и авторизуйтесь заново

### Ошибка миграций
```bash
alembic stamp head  # Отметить как применённую
alembic upgrade head  # Применить
```

### TgCrypto missing
Pyrogram работает и без TgCrypto, но медленнее. Для ускорения на Linux:
```bash
pip install tgcrypto
```
На Windows требует MSVC Build Tools.

## 📝 TODO

- [ ] Парсинг истории чатов (retrospective)
- [ ] Экспорт данных в CSV/JSON
- [ ] Фильтры по датам
- [ ] Статистика и графики
- [ ] Мультиязычность
- [ ] Webhook режим
- [ ] Тесты (pytest)

## 👨‍💻 Автор

Разработано с ❤️ для портфолио

**Стек:** Aiogram 3 + Pyrogram + SQLAlchemy + Redis + Pydantic + Loguru

## 📄 Лицензия

MIT
