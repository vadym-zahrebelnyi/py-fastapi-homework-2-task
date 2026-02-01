from typing import Annotated

from pydantic import BaseModel, Field, ConfigDict


class CountryCreate(BaseModel):
    code: Annotated[str, Field(min_length=3, max_length=3)]
    name: Annotated[str | None, Field(max_length=255)] = None


class CountryResponse(BaseModel):
    id: int
    code: str
    name: str | None = None

    model_config = ConfigDict(from_attributes=True)
