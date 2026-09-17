# Дизайн: netschool-api (HTTP API Сетевого города)

Дата: 2026-09-17.
Статус: draft (ожидает ревью пользователя).

## 1. Цель

Отдельный HTTP-сервис, отдающий данные Сетевого города (домашние задания,
в будущем — оценки и другие ресурсы) в формате JSON по секретному токену.
Изначально работает локально, планируется деплой на тот же Debian-сервер,
где живёт Telegram-бот `tg-bot-grades`.

## 2. Стек

- Python 3.12
- FastAPI + Uvicorn
- `netschoolapi-plus` (форк `freeuser3/netschool-api-plus`) как git-зависимость
- pydantic для моделей ответа
- pytest + httpx TestClient для тестов

## 3. Репозиторий

Имя: `netschool-api` (GitHub, пользователь `freeuser3`).
Локализация: `C:\Users\max\Documents\netschool-api`.

## 4. Конфигурация

Файл `config.json` (gitignored):

```json
{
  "ns_login": "...",
  "ns_password": "...",
  "ns_school": "...",
  "api_token": "..."
}
```

- `api_token` может быть переопределён переменной окружения `API_TOKEN`
  (она имеет приоритет).
- Пример конфига: `config.example.json`.

## 5. Авторизация

Один статичный Bearer-токен.

- Все эндпоинты, кроме `/healthz`, требуют заголовок
  `Authorization: Bearer <token>`.
- Без токена / с неверным токеном: `401 {"detail": "Invalid token"}`.
- Реализация: FastAPI-зависимость, сравнивающая токен с конфигом
  (константное время).

## 6. Эндпоинты (версия /v1)

| Метод | Путь                        | Токен | Описание                     |
|-------|------------------------------|-------|------------------------------|
| GET   | `/healthz`                   | нет   | проверка живости            |
| GET   | `/v1/homework?date=YYYY-MM-DD` | да  | домашние задания на дату    |

Пространство `/v1` оставляет место для будущих ресурсов:
`/v1/grades`, `/v1/diary`, `/v1/announcements` и т. п.

### GET /healthz

Ответ:
```json
{ "status": "ok" }
```

### GET /v1/homework?date=YYYY-MM-DD

Параметры:

- `date` (обязательный) — дата в формате `YYYY-MM-DD`.

Семантика:

- Рассматривается строго указанная дата без сдвига на ближайший учебный день.
- Если на дату есть хотя бы один урок — `school_day: true`.
- Если уроков нет — `school_day: false`, `homework: []`.
- Если уроки есть, но домашних заданий нет — `school_day: true`, `homework: []`.

Успешный ответ `200`:

```json
{
  "date": "2026-09-15",
  "school_day": true,
  "homework": [
    {
      "subject": "Английский язык",
      "lesson_number": 4,
      "content": "SB стр. 138 упр. 1-2 (повторить Present Tenses).",
      "attachments": [
        { "name": "Superstitions.pdf", "type": "pdf" }
      ]
    }
  ]
}
```

Структуры:

- `HomeworkItem`:
  - `subject: str` — предмет
  - `lesson_number: int` — номер урока в расписании (1-based, `number + 1`)
  - `content: str` — текст домашнего задания
  - `attachments: list[Attachment]` — вложения
- `Attachment`:
  - `name: str` — имя файла
  - `type: str` — категория по расширению:
    `image`, `word` (doc/docx), `spreadsheet` (xls/xlsx),
    `presentation` (ppt/pptx), `archive` (zip/rar/7z), `pdf`, `other`
- `HomeworkResponse`:
  - `date: str` — запрошенная дата `YYYY-MM-DD`
  - `school_day: bool`
  - `homework: list[HomeworkItem]`

Ошибки:

- `400` — невалидный формат даты → `{"detail": "Invalid date format"}`
- `401` — отсутствует/неверный токен → `{"detail": "Invalid token"}`
- `502` — ошибка обращения к Сетевому городу (логин, сеть, парсинг)
  → `{"detail": "<сообщение об ошибке>"}`

## 7. Структура проекта

```
netschool-api/
  app/
    __init__.py
    config.py       # загрузка конфига, приоритет API_TOKEN
    auth.py         # FastAPI-зависимость проверки Bearer-токена
    homework.py     # fetch_homework(date) -> структура JSON
    models.py       # pydantic-модели (HomeworkItem, Attachment, ...)
    main.py         # FastAPI-приложение, эндпоинты /healthz, /v1/homework
  tests/
    __init__.py
    test_homework.py
    test_auth.py
  requirements.txt
  config.example.json
  README.md
  .gitignore
```

## 8. Логика получения домашки

В `app/homework.py`:

1. `load_config()` из `app/config.py` — читает `config.json`.
2. `async def fetch_homework(requested: date) -> HomeworkResponse`:
   - `NetSchoolAPI("https://sgo.e-mordovia.ru")`
   - `login()`
   - `diary(start=requested, end=requested)`
   - для каждого урока, у каждого `assignment` с `type == "Домашнее задание"`
     собрать `HomeworkItem`.
   - для каждого такого задания получить вложения
     `ns.attachments(assignment_id)` → имена файлов → тип по расширению.
   - `logout()` в `finally`.
3. `attachment_type(filename) -> str` — чистая функция категоризации
   расширения (переносится из бота `grades.py::attachment_icon`, только
   возвращает строку категории вместо эмодзи).

## 9. Обработка ошибок

- Ошибки логина/сети во `fetch_homework` ловятся на уровне эндпоинта
  и превращаются в `502` с текстом причины.
- FastAPI выбрасывает `400`/`401` через `HTTPException`.

## 10. Тестирование

pytest + FastAPI TestClient:

- `test_auth.py`:
  - без токена → 401
  - неверный токен → 401
  - `/healthz` без токена → 200
- `test_homework.py`:
  - есть домашки (мок diary/attachments) → 200, корректная структура
  - уроки есть, домашек нет → `school_day: true`, `homework: []`
  - нет уроков (выходной) → `school_day: false`, `homework: []`
  - невалидный формат даты → 400
  - ошибка СГО → 502

Для тестов мокается `NetSchoolAPI` из `net-school-api-plus`.

## 11. Запуск (локально)

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

Деплой на Debian — по образцу бота (systemd/`nohup`), описывается позднее
после проверки на сервере.

## 12. Файл .gitignore

- `.venv/`
- `config.json`
- `__pycache__/`
- `.pytest_cache/`
- `*.pyc`