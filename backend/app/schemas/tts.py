from typing import Literal

from pydantic import BaseModel, Field


class SynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    language: Literal["te-IN", "en-IN", "auto"] | None = None
    voice: str | None = Field(default=None, min_length=1, max_length=80)
