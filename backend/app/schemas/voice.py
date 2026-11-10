from pydantic import BaseModel


class TranscriptionResponse(BaseModel):
    success: bool
    transcript: str
    model: str
    request_id: str | None
    language: str
