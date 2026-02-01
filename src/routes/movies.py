from typing import Annotated, Type, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, Request
from pydantic import ValidationError
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas import (
    MoviesList,
    PaginationParams,
    MovieResponse,
    MovieCreate,
    MovieUpdate,
)


router = APIRouter()
Database = Annotated[AsyncSession, Depends(get_db)]
T = TypeVar("T", CountryModel, GenreModel, ActorModel, LanguageModel)


async def _get_or_create_related_entity(
    db: AsyncSession, model: Type[T], name: str, lookup_field: str = "name"
) -> T:
    if instance := await db.scalar(
        select(model).where(getattr(model, lookup_field) == name)
    ):
        return instance

    new_instance = model(**{lookup_field: name})
    db.add(new_instance)
    return new_instance


async def _get_or_create_related_entities(
    db: AsyncSession, model: Type[T], names: list[str]
) -> list[T]:
    if not names:
        return []

    db_entities = (await db.scalars(select(model).where(model.name.in_(names)))).all()

    new_entities = []
    if new_names := set(names) - {entity.name for entity in db_entities}:
        new_entities = [model(name=name) for name in new_names]
        db.add_all(new_entities)

    return list(db_entities) + new_entities


@router.get("/movies/", response_model=MoviesList)
async def get_movie_list(
    db: Database, pg_params: Annotated[PaginationParams, Query()]
) -> MoviesList:
    total_items = await db.scalar(select(func.count(MovieModel.id))) or 0
    pg_params.check_bounds(total_items=total_items, msg="No movies found.")

    query = (
        select(MovieModel)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
        .order_by(MovieModel.id.desc())
        .offset(pg_params.offset)
        .limit(pg_params.per_page)
    )
    fetched_movies = (await db.scalars(query)).all()

    return MoviesList(
        movies=list(fetched_movies),
        **pg_params.get_metadata(
            total_items=total_items, prefix_url="/theater/movies/"
        ).model_dump(),
    )


@router.post(
    "/movies/", response_model=MovieResponse, status_code=status.HTTP_201_CREATED
)
async def create_movie(request: Request, db: Database) -> MovieResponse:
    try:
        json_data = await request.json()
        movie_data = MovieCreate.model_validate(json_data)
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data.",
        )

    db_movie = (
        await db.scalars(
            select(MovieModel).where(
                MovieModel.name == movie_data.name, MovieModel.date == movie_data.date
            )
        )
    ).first()
    movie_data.check_unique_movie_constraint(db_movie=db_movie)

    new_movie = MovieModel(
        **movie_data.model_dump(exclude={"country", "genres", "actors", "languages"}),
        country=await _get_or_create_related_entity(
            db, CountryModel, movie_data.country, lookup_field="code"
        ),
        genres=await _get_or_create_related_entities(db, GenreModel, movie_data.genres),
        actors=await _get_or_create_related_entities(db, ActorModel, movie_data.actors),
        languages=await _get_or_create_related_entities(
            db, LanguageModel, movie_data.languages
        ),
    )

    db.add(new_movie)
    await db.commit()
    await db.refresh(new_movie, ["country", "genres", "actors", "languages"])

    return MovieResponse.model_validate(new_movie)


@router.get("/movies/{movie_id}/", response_model=MovieResponse)
async def get_movie(
    db: Database, movie_id: Annotated[int, Path(ge=1)]
) -> MovieResponse:
    if movie := await db.scalar(
        select(MovieModel)
        .where(MovieModel.id == movie_id)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
    ):
        return MovieResponse.model_validate(movie)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Movie with the given ID was not found.",
    )


@router.delete("/movies/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(movie_id: int, db: Database) -> None:
    movie = await db.get(MovieModel, movie_id)

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )

    await db.delete(movie)
    await db.commit()


@router.patch("/movies/{movie_id}/", response_model=dict)
async def update_movie(movie_id: int, request: Request, db: Database) -> dict:
    movie = await db.get(MovieModel, movie_id)

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )

    try:
        json_data = await request.json()
        update_data = MovieUpdate.model_validate(json_data)
    except (ValidationError, Exception):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data.",
        )

    update_data_dict = update_data.model_dump(exclude_unset=True)

    for field, value in update_data_dict.items():
        setattr(movie, field, value)

    db.add(movie)
    await db.commit()
    await db.refresh(movie)

    return {"detail": "Movie updated successfully."}
