from typing import Annotated

from pydantic import BaseModel, Field, ConfigDict


class LanguageCreate(BaseModel):
    name: Annotated[str, Field(max_length=255)]


class LanguageResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)
