from typing import Annotated

from pydantic import BaseModel, Field, ConfigDict


class ActorCreate(BaseModel):
    name: Annotated[str, Field(max_length=255)]


class ActorResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)
