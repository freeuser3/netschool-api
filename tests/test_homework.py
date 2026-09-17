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


def test_homework_empty_schedule(monkeypatch):
    from netschoolapi_plus.schemas import Diary

    monkeypatch.setenv("API_TOKEN", "sekret")
    diary = Diary(
        start=datetime.date(2026, 9, 15),
        end=datetime.date(2026, 9, 15),
        schedule=[],
    )
    ns = _mock_ns(diary)
    with patch("app.homework.load_config") as mock_cfg, \
         patch("app.homework.NetSchoolAPI") as mock_ns_cls:
        mock_cfg.return_value = _config()
        mock_ns_cls.return_value = ns

        r = client.get("/v1/homework?date=2026-09-15", headers=AUTH)

    assert r.status_code == 200
    data = r.json()
    assert data["school_day"] is False
    assert data["homework"] == []


def test_homework_attachments_failure(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "sekret")
    diary = _make_diary(
        [_make_lesson(3, "Английский язык",
                      [_make_assignment(12, "Домашнее задание", "SB стр. 138")])]
    )
    ns = _mock_ns(diary)
    ns.attachments = AsyncMock(side_effect=RuntimeError("net error"))
    with patch("app.homework.load_config") as mock_cfg, \
         patch("app.homework.NetSchoolAPI") as mock_ns_cls:
        mock_cfg.return_value = _config()
        mock_ns_cls.return_value = ns

        r = client.get("/v1/homework?date=2026-09-15", headers=AUTH)

    assert r.status_code == 200
    data = r.json()
    assert data["homework"][0]["attachments"] == []


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
    ns.logout.assert_awaited_once()


from app.homework import attachment_type


def test_homework_invalid_date(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "sekret")
    r = client.get("/v1/homework?date=15-09-2026", headers=AUTH)
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid date format"


def test_attachment_type():
    assert attachment_type("photo.png") == "image"
    assert attachment_type("photo.JPG") == "image"
    assert attachment_type("photo.jpeg") == "image"
    assert attachment_type("photo.gif") == "image"
    assert attachment_type("photo.bmp") == "image"
    assert attachment_type("photo.webp") == "image"
    assert attachment_type("doc.docx") == "word"
    assert attachment_type("doc.doc") == "word"
    assert attachment_type("file.pdf") == "pdf"
    assert attachment_type("table.xlsx") == "spreadsheet"
    assert attachment_type("table.xls") == "spreadsheet"
    assert attachment_type("p.pptx") == "presentation"
    assert attachment_type("p.ppt") == "presentation"
    assert attachment_type("a.rar") == "archive"
    assert attachment_type("a.zip") == "archive"
    assert attachment_type("a.7z") == "archive"
    assert attachment_type("notes.txt") == "other"
    assert attachment_type("unknown.xyz") == "other"
