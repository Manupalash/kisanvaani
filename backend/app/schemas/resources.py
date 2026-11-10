from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class FarmerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    village: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    land_area_acres: float | None = Field(default=None, ge=0)
    preferred_language: str = Field(default="te", max_length=20)


class FarmerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    village: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    land_area_acres: float | None = Field(default=None, ge=0)
    preferred_language: str | None = Field(default=None, max_length=20)


class FarmerRead(ORMModel):
    id: int
    name: str
    phone: str | None
    village: str | None
    district: str | None
    land_area_acres: float | None
    preferred_language: str


class CropCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    variety: str | None = Field(default=None, max_length=100)
    season: str | None = Field(default=None, max_length=60)
    stage: str | None = Field(default=None, max_length=60)
    area_acres: float | None = Field(default=None, ge=0)


class CropRead(ORMModel):
    id: int
    farmer_id: int
    name: str
    variety: str | None
    season: str | None
    stage: str | None
    area_acres: float | None


class ConversationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    language: str = Field(default="te", max_length=20)


class ConversationRead(ORMModel):
    id: int
    farmer_id: int
    title: str
    language: str


class MessageCreate(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    text: str | None = Field(default=None, max_length=10000)
    audio_mime_type: str | None = Field(default=None, max_length=80)


class MessageRead(ORMModel):
    id: int
    conversation_id: int
    role: str
    text: str | None
    audio_mime_type: str | None


class AdvisoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)
    category: str = Field(default="general", max_length=80)
    is_demo: bool = False


class AdvisoryRead(ORMModel):
    id: int
    farmer_id: int
    title: str
    body: str
    category: str
    is_demo: bool


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    source: str | None = Field(default=None, max_length=300)
    language: str = Field(default="te", max_length=20)
    content: str = Field(min_length=1, max_length=50000)
    crop: str | None = Field(default=None, max_length=100)
    topic: str | None = Field(default=None, max_length=100)
    source_name: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=1000)


class DocumentRead(ORMModel):
    id: int
    farmer_id: int | None
    title: str
    source: str | None
    language: str
    content: str
    crop: str | None
    topic: str | None
    source_name: str | None
    source_url: str | None
