# netschool-api Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать HTTP-сервис, который возвращает домашние задания Сетевого города в формате JSON по секретному Bearer-токену.

**Architecture:** FastAPI-приложение с двумя эндпоинтами (`/healthz`, `/v1/homework`). Одна учётка СГО берётся из `config.json`, данные читаются через форк `netschoolapi-plus` (`diary`, `attachments`). Auth — FastAPI-зависимость, сравнивающая Bearer-токен с конфигом.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, pydantic v2, `netschoolapi-plus` (git), pytest + httpx TestClient.

**Spec:** `docs/superpowers/specs/2026-09-17-netschool-api-design.md`

## Global Constraints

- Python 3.12, кодировка файлов UTF-8.
- Единственная зависимость от СГО — форк `netschoolapi-plus @ git+https://github.com/freeuser3/netschool-api-plus.git`.
- `config.json` в `.gitignore`; токен не коммитить.
- Все эндпоинты кроме `/healthz` требуют `Authorization: Bearer <token>`; неверный/отсутствующий токен → `401 {"detail": "Invalid token"}`.
- `/v1/homework` принимает обязательный `date` в `YYYY-MM-DD`, строго без сдвига на следующий учебный день.
- Тип вложений — строка категории: `image`, `word`, `spreadsheet`, `presentation`, `archive`, `pdf`, иначе `other`. Файлы не скачиваются.
- Домашки — это `assignment.type == "Домашнее задание"`; номер урока 1-based (`number + 1`).
- Ошибка СГО/сети → `502`; невалидная дата → `400`.
- Статус spec: `draft` → после ревью пользователем `approved`.

---

### Task 1: Скаффолдинг проекта и конфиг

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `config.example.json`
- Create: `app/__init__.py`
- Create: `tests/__init__.py`
- Create: `app/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `app.config.load_config(path="config.json") -> dict` — читает JSON-файл (UTF-8).
- Produces: `app.config.get_api_token() -> str` — возвращает `API_TOKEN` из env, если задан, иначе `load_config()["api_token"]`.

- [ ] **Step 1: Create `.gitignore`**

```
.venv/
config.json
__pycache__/
.pytest_cache/
*.pyc
```

- [ ] **Step 2: Create `requirements.txt`**

```
fastapi>=0.110,<1.0
uvicorn[standard]>=0.29,<1.0
pydantic>=2.4,<3.0
httpx>=0.27,<1.0
pytest>=8.0,<9.0
netschoolapi-plus @ git+https://github.com/freeuser3/netschool-api-plus.git
```

- [ ] **Step 3: Create `config.example.json`**

```json
{
  "ns_login": "your_login",
  "ns_password": "your_password",
  "ns_school": "School Name",
  "api_token": "secret-token"
}
```

- [ ] **Step 4: Create empty package init files**

`app/__init__.py` и `tests/__init__.py` — пустые файлы.

- [ ] **Step 5: Create `app/config.py`**

```python
import json
import os


def load_config(path: str = "config.json") -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_api_token() -> str:
    env_token = os.environ.get("API_TOKEN")
    if env_token:
        return env_token
    return load_config()["api_token"]
```

- [ ] **Step 6: Write the failing test `tests/test_config.py`**

```python
import json

from app import config as cfg


def test_load_config_reads_file(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"api_token": "abc"}), encoding="utf-8")
    assert cfg.load_config(str(p))["api_token"] == "abc"


def test_get_api_token_prefers_env(monkeypatch, tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"api_token": "file_token"}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("API_TOKEN", "env_token")
    assert cfg.get_api_token() == "env_token"


def test_get_api_token_falls_back_to_file(monkeypatch, tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"api_token": "file_token"}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("API_TOKEN", raising=False)
    assert cfg.get_api_token() == "file_token"
```

- [ ] **Step 7: Install dependencies and run test to verify it passes**

Run: `python -m pip install -r requirements.txt`
Run: `python -m pytest tests/test_config.py -v`
Expected: 3 passed.

- [ ] **Step 8: Commit**

```bash
git add .gitignore requirements.txt config.example.json app/__init__.py tests/__init__.py app/config.py tests/test_config.py
git commit -m "feat: project scaffold and config module"
```

---

### Task 2: Pydantic-модели

**Files:**
- Create: `app/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `app.models.Attachment(BaseModel)` — поля `name: str`, `type: str`.
- Produces: `app.models.HomeworkItem(BaseModel)` — поля `subject: str`, `lesson_number: int`, `content: str`, `attachments: list[Attachment]`.
- Produces: `app.models.HomeworkResponse(BaseModel)` — поля `date: str`, `school_day: bool`, `homework: list[HomeworkItem]`.

- [ ] **Step 1: Write the failing test `tests/test_models.py`**

```python
from app.models import Attachment, HomeworkItem, HomeworkResponse


def test_homework_response_serializes_to_spec_shape():
    resp = HomeworkResponse(
        date="2026-09-15",
        school_day=True,
        homework=[
            HomeworkItem(
                subject="Английский язык",
                lesson_number=4,
                content="SB стр. 138 упр. 1-2",
                attachments=[Attachment(name="Superstitions.pdf", type="pdf")],
            )
        ],
    )
    assert resp.model_dump() == {
        "date": "2026-09-15",
        "school_day": True,
        "homework": [
            {
                "subject": "Английский язык",
                "lesson_number": 4,
                "content": "SB стр. 138 упр. 1-2",
                "attachments": [{"name": "Superstitions.pdf", "type": "pdf"}],
            }
        ],
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models'`.

- [ ] **Step 3: Create `app/models.py`**

```python
from pydantic import BaseModel


class Attachment(BaseModel):
    name: str
    type: str


class HomeworkItem(BaseModel):
    subject: str
    lesson_number: int
    content: str
    attachments: list[Attachment]


class HomeworkResponse(BaseModel):
    date: str
    school_day: bool
    homework: list[HomeworkItem]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_models.py
git commit -m "feat: pydantic response models"
```

---

### Task 3: Логика получения домашки

**Files:**
- Create: `app/homework.py`
- Test: `tests/test_homework.py`

**Interfaces:**
- Consumes: `app.config.load_config()` (Task 1), `app.models.HomeworkResponse/HomeworkItem/Attachment` (Task 2).
- Produces: `app.homework.HOMEWORK_TYPE` = `"Домашнее задание"`.
- Produces: `app.homework.attachment_type(filename) -> str`.
- Produces: `app.homework.fetch_homework(requested: datetime.date) -> HomeworkResponse` — логинит в СГО, читает `diary(start=requested, end=requested)`, собирает домашки и вложения, в `finally` делает `logout()`.

- [ ] **Step 1: Write the failing test `tests/test_homework.py`**

```python
import datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _config():
    return {
        "ns_login": "user",
        "ns_password": "pass",
        "ns_school": "School",
    }


def _make_assignment(aid, type_, content):
    from netschoolapi_plus.schemas import Assignment

    return Assignment(
        id=aid,
        comment="",
        type=type_,
        content=content,
        mark=None,
        is_duty=False,
        deadline=datetime.date(2026, 9, 15),
    )


def _make_lesson(number, subject, assignments):
    from netschoolapi_plus.schemas import Lesson

    return Lesson(
        day=datetime.date(2026, 9, 15),
        start=datetime.time(9, 0),
        end=datetime.time(9, 45),
        room="101",
        number=number,
        subject=subject,
        assignments=assignments,
    )


def _make_diary(lessons, day=datetime.date(2026, 9, 15)):
    from netschoolapi_plus.schemas import Day, Diary

    return Diary(
        start=day,
        end=day,
        schedule=[Day(lessons=lessons, day=day)],
    )


def _mock_ns(diary, attachments=None):
    mock_ns = AsyncMock()
    mock_ns.login = AsyncMock()
    mock_ns.logout = AsyncMock()
    mock_ns.diary = AsyncMock(return_value=diary)
    mock_ns.attachments = AsyncMock(return_value=attachments or [])
    return mock_ns


AUTH = {"Authorization": "Bearer sekret"}


def test_homework_returns_items(monkeypatch):
    from netschoolapi_plus.schemas import Attachment

    monkeypatch.setenv("API_TOKEN", "sekret")
    diary = _make_diary(
        [
            _make_lesson(
                3,
                "Английский язык",
                [_make_assignment(12, "Домашнее задание", "SB стр. 138 упр. 1-2")],
            ),
            _make_lesson(
                0,
                "Биология",
                [_make_assignment(11, "Ответ на уроке", "---Не указана---")],
            ),
        ]
    )
    ns = _mock_ns(
        diary,
        [Attachment(id=1, name="Superstitions.pdf", description="")],
    )
    with patch("app.homework.load_config") as mock_cfg, \
         patch("app.homework.NetSchoolAPI") as mock_ns_cls:
        mock_cfg.return_value = _config()
        mock_ns_cls.return_value = ns

        r = client.get("/v1/homework?date=2026-09-15", headers=AUTH)

    assert r.status_code == 200
    data = r.json()
    assert data["date"] == "2026-09-15"
    assert data["school_day"] is True
    assert len(data["homework"]) == 1
    item = data["homework"][0]
    assert item["subject"] == "Английский язык"
    assert item["lesson_number"] == 4
    assert item["content"] == "SB стр. 138 упр. 1-2"
    assert item["attachments"] == [{"name": "Superstitions.pdf", "type": "pdf"}]


def test_homework_lessons_without_homework(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "sekret")
    diary = _make_diary(
        [_make_lesson(0, "Биология", [_make_assignment(1, "Ответ на уроке", "---")])]
    )
    ns = _mock_ns(diary)
    with patch("app.homework.load_config") as mock_cfg, \
         patch("app.homework.NetSchoolAPI") as mock_ns_cls:
        mock_cfg.return_value = _config()
        mock_ns_cls.return_value = ns

        r = client.get("/v1/homework?date=2026-09-15", headers=AUTH)

    assert r.status_code == 200
    data = r.json()
    assert data["school_day"] is True
    assert data["homework"] == []


def test_homework_no_school_day(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "sekret")
    diary = _make_diary([], day=datetime.date(2026, 9, 19))
    ns = _mock_ns(diary)
    with patch("app.homework.load_config") as mock_cfg, \
         patch("app.homework.NetSchoolAPI") as mock_ns_cls:
        mock_cfg.return_value = _config()
        mock_ns_cls.return_value = ns

        r = client.get("/v1/homework?date=2026-09-19", headers=AUTH)

    assert r.status_code == 200
    data = r.json()
    assert data["school_day"] is False
    assert data["homework"] == []


def test_homework_sgo_error(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "sekret")
    ns = AsyncMock()
    ns.login = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("app.homework.load_config") as mock_cfg, \
         patch("app.homework.NetSchoolAPI") as mock_ns_cls:
        mock_cfg.return_value = _config()
        mock_ns_cls.return_value = ns

        r = client.get("/v1/homework?date=2026-09-15", headers=AUTH)

    assert r.status_code == 502
    assert "boom" in r.json()["detail"]
```

Примечание: тесты ссылаются на `app.main` — создаём в Task 4. Для этого шага тесты будут падать только на этапе Task 4 полностью; здесь цель — протестировать `attachment_type` отдельно.

- [ ] **Step 2: Add `attachment_type` test to `tests/test_homework.py`**

```python
from app.homework import attachment_type


def test_attachment_type():
    assert attachment_type("photo.png") == "image"
    assert attachment_type("photo.JPG") == "image"
    assert attachment_type("doc.docx") == "word"
    assert attachment_type("doc.doc") == "word"
    assert attachment_type("file.pdf") == "pdf"
    assert attachment_type("table.xlsx") == "spreadsheet"
    assert attachment_type("p.pptx") == "presentation"
    assert attachment_type("a.rar") == "archive"
    assert attachment_type("notes.txt") == "other"
```

- [ ] **Step 3: Run test to verify `test_attachment_type` fails**

Run: `python -m pytest tests/test_homework.py::test_attachment_type -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.homework'`.

- [ ] **Step 4: Create `app/homework.py`**

```python
import datetime
import os
from typing import List

from netschoolapi_plus import NetSchoolAPI

from app.config import load_config
from app.models import Attachment, HomeworkItem, HomeworkResponse

HOMEWORK_TYPE = "Домашнее задание"

ATTACHMENT_TYPES = {
    "image": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"},
    "word": {".doc", ".docx"},
    "spreadsheet": {".xls", ".xlsx"},
    "presentation": {".ppt", ".pptx"},
    "archive": {".zip", ".rar", ".7z"},
    "pdf": {".pdf"},
}


def attachment_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].casefold()
    for category, extensions in ATTACHMENT_TYPES.items():
        if ext in extensions:
            return category
    return "other"


async def _attachments(ns, assignment_id: int) -> List[Attachment]:
    try:
        attachments = await ns.attachments(assignment_id)
    except Exception:
        return []
    return [Attachment(name=a.name, type=attachment_type(a.name)) for a in attachments]


async def fetch_homework(requested: datetime.date) -> HomeworkResponse:
    config = load_config()
    ns = NetSchoolAPI("https://sgo.e-mordovia.ru")
    try:
        await ns.login(
            config["ns_login"],
            config["ns_password"],
            config["ns_school"],
        )
        diary = await ns.diary(start=requested, end=requested)
        day = next((d for d in diary.schedule if d.day == requested), None)
        items: List[HomeworkItem] = []
        if day:
            for lesson in sorted(day.lessons, key=lambda l: l.number):
                for assignment in lesson.assignments:
                    if assignment.type != HOMEWORK_TYPE:
                        continue
                    attachments = await _attachments(ns, assignment.id)
                    items.append(HomeworkItem(
                        subject=lesson.subject,
                        lesson_number=lesson.number + 1,
                        content=assignment.content,
                        attachments=attachments,
                    ))
        return HomeworkResponse(
            date=requested.isoformat(),
            school_day=bool(day and day.lessons),
            homework=items,
        )
    finally:
        try:
            await ns.logout()
        except Exception:
            pass
```

- [ ] **Step 5: Run `test_attachment_type` to verify it passes**

Run: `python -m pytest tests/test_homework.py::test_attachment_type -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/homework.py tests/test_homework.py
git commit -m "feat: homework fetch logic and attachment type mapping"
```

---

### Task 4: Auth-зависимость и FastAPI-приложение

**Files:**
- Create: `app/auth.py`
- Create: `app/main.py`
- Test: `tests/test_auth.py`

**Interfaces:**
- Consumes: `app.config.get_api_token()` (Task 1), `app.homework.fetch_homework()` (Task 3), `app.models.HomeworkResponse` (Task 2).
- Produces: `app.auth.require_token(authorization: str | None = Header(default=None)) -> None` — FastAPI-зависимость, бросает `HTTPException(401)` при отсутствии/неверном токене.
- Produces: `app.main.app` — FastAPI-приложение с `GET /healthz` и `GET /v1/homework?date=...`.

- [ ] **Step 1: Write the failing test `tests/test_auth.py`**

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz_without_token(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "sekret")
    assert client.get("/healthz").status_code == 200


def test_homework_without_token(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "sekret")
    r = client.get("/v1/homework?date=2026-09-15")
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid token"


def test_homework_with_wrong_token(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "sekret")
    r = client.get(
        "/v1/homework?date=2026-09-15",
        headers={"Authorization": "Bearer wrong"},
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid token"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_auth.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 3: Create `app/auth.py`**

```python
from fastapi import Header, HTTPException

from app.config import get_api_token


def require_token(authorization: str | None = Header(default=None)) -> None:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != get_api_token():
        raise HTTPException(status_code=401, detail="Invalid token")
```

- [ ] **Step 4: Create `app/main.py`**

```python
import datetime

from fastapi import Depends, FastAPI, HTTPException

from app.auth import require_token
from app.homework import fetch_homework
from app.models import HomeworkResponse

app = FastAPI()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/v1/homework", dependencies=[Depends(require_token)])
async def get_homework(date: str) -> HomeworkResponse:
    try:
        requested = datetime.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    try:
        return await fetch_homework(requested)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
```

- [ ] **Step 5: Run all tests to verify they pass**

Run: `python -m pytest -v`
Expected: all tests pass: `test_auth.py` (3), `test_config.py` (3), `test_models.py` (1), `test_homework.py` (5).

- [ ] **Step 6: Add invalid-date test and run**

Добавить в `tests/test_homework.py`:

```python
def test_homework_invalid_date(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "sekret")
    r = client.get("/v1/homework?date=15-09-2026", headers=AUTH)
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid date format"
```

Run: `python -m pytest tests/test_homework.py::test_homework_invalid_date -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/auth.py app/main.py tests/test_auth.py tests/test_homework.py
git commit -m "feat: FastAPI app with auth and /v1/homework endpoint"
```

---

### Task 5: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md`**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README"
```

---

### Task 6: Публикация на GitHub и обновление статуса spec

**Files:**
- Modify: `docs/superpowers/specs/2026-09-17-netschool-api-design.md` (статус)

- [ ] **Step 1: Verify `gh` CLI available and authenticated**

Run: `gh auth status`
Expected: authenticated as user.

- [ ] **Step 2: Create GitHub repo and push**

Run:
```
gh repo create freeuser3/netschool-api --public --source . --remote origin --push
```

- [ ] **Step 3: Update spec status to approved**

В `docs/superpowers/specs/2026-09-17-netschool-api-design.md` заменить:

```markdown
Статус: draft (ожидает ревью пользователя).
```

на

```markdown
Статус: approved (после ревью пользователя).
```

- [ ] **Step 4: Commit spec status change and push**

```bash
git add docs/superpowers/specs/2026-09-17-netschool-api-design.md
git commit -m "docs: mark netschool-api design spec approved"
git push
```

- [ ] **Step 5: Final verification**

Run: `python -m pytest -v`
Expected: all 12 tests pass.