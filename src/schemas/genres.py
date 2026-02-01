from typing import Annotated

from pydantic import BaseModel, Field, ConfigDict


class GenreCreate(BaseModel):
    name: Annotated[str, Field(max_length=255)]


class GenreResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)
