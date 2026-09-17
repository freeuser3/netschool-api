# netschool-api

HTTP API для доступа к данным Сетевого города (домашние задания, в будущем —
оценки и другие ресурсы). Секретный доступ по Bearer-токену.

## Установка

```bash
python -m venv .venv
# Windows
.venv\Scripts\pip install -r requirements.txt
# Linux
.venv/bin/pip install -r requirements.txt
```

## Конфигурация

Скопируйте `config.example.json` в `config.json` и заполните:

```json
{
  "ns_login": "",
  "ns_password": "",
  "ns_school": "",
  "api_token": ""
}
```

`api_token` также можно задать переменной окружения `API_TOKEN` — она
имеет приоритет над файлом.

## Запуск

```bash
uvicorn app.main:app --port 8000
```

## Эндпоинты

### GET /healthz

Проверка живости, без токена.

```bash
curl http://localhost:8000/healthz
# {"status":"ok"}
```

### GET /v1/homework?date=YYYY-MM-DD

Домашние задания на дату. Требуется заголовок:

```
Authorization: Bearer <api_token>
```

Ответ:

```json
{
  "date": "2026-09-15",
  "school_day": true,
  "homework": [
    {
      "subject": "Английский язык",
      "lesson_number": 4,
      "content": "SB стр. 138 упр. 1-2 (повторить Present Tenses).",
      "attachments": [{"name": "Superstitions.pdf", "type": "pdf"}]
    }
  ]
}
```

Ошибки: `400` — невалидный формат даты, `401` — неверный токен,
`502` — ошибка обращения к Сетевому городу.

## Тесты

```bash
python -m pytest
```
