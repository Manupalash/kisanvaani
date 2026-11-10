from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: int = Field(gt=0)
    farmer_id: int = Field(gt=0)
    message: str = Field(min_length=1, max_length=10000)
    request_id: str | None = Field(default=None, min_length=1, max_length=64)


class RetrievedSourceRead(BaseModel):
    id: int
    title: str
    content: str
    source_name: str | None
    source_url: str | None
    crop: str | None
    topic: str | None


class ChatResponse(BaseModel):
    answer: str
    language: str
    retrieved_sources: list[RetrievedSourceRead]
    conversation_id: int
