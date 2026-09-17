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
