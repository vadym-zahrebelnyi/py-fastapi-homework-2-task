import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, get_type_hints

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, ConfigDict, field_validator, create_model

from database import MovieModel
from database.models import MovieStatusEnum
from schemas import countries, genres, actors, languages


class MovieBaseResponse(BaseModel):
    id: int
    name: str
    date: datetime.date
    score: float
    overview: str

    model_config = ConfigDict(from_attributes=True)


class MoviesListItem(MovieBaseResponse):
    pass


class MoviesList(BaseModel):
    movies: list[MoviesListItem]
    prev_page: str | None = None
    next_page: str | None = None
    total_pages: int
    total_items: int


class MovieCreate(BaseModel):
    name: Annotated[str, Field(max_length=255)]
    date: datetime.date
    score: Annotated[float, Field(ge=0, le=100)]
    overview: str
    status: MovieStatusEnum
    budget: Annotated[Decimal, Field(ge=0, max_digits=15, decimal_places=2)]
    revenue: Annotated[float, Field(ge=0)]
    country: Annotated[str, Field(max_length=3)]
    genres: Annotated[list[str], Field(max_length=255)]
    actors: Annotated[list[str], Field(max_length=255)]
    languages: Annotated[list[str], Field(max_length=255)]

    @field_validator("budget", mode="before")
    @classmethod
    def round_money(cls, value):
        return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @field_validator("date")
    @classmethod
    def date_not_too_far_in_future(cls, value):
        if value > datetime.date.today() + datetime.timedelta(days=365):
            raise ValueError("Date cannot be more than one year in the future")
        return value

    def check_unique_movie_constraint(self, db_movie: MovieModel) -> None:
        if db_movie:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"A movie with the name '{self.name}' "
                    f"and release date '{self.date}' already exists."
                ),
            )


class MovieResponse(MovieBaseResponse):
    status: str
    budget: float
    revenue: float
    country: countries.CountryResponse
    genres: list[genres.GenreResponse]
    actors: list[actors.ActorResponse]
    languages: list[languages.LanguageResponse]


MovieUpdate = create_model(
    "MovieUpdate",
    __base__=MovieCreate,
    **{k: (v | None, None) for k, v in get_type_hints(MovieCreate).items()},
)
