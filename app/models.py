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
