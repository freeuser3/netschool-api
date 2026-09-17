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
