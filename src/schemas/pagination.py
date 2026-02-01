import math
from typing import Annotated

from fastapi import HTTPException, status
from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    total_pages: int
    total_items: int
    prev_page: str | None
    next_page: str | None


class PaginationParams(BaseModel):
    page: Annotated[int, Field(1, ge=1)]
    per_page: Annotated[int, Field(10, ge=1, le=20)]

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    def check_bounds(self, total_items: int, msg: str) -> None:
        if total_items == 0 or self.offset >= total_items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    def get_metadata(self, total_items: int, prefix_url: str) -> PaginationMeta:
        total_pages = math.ceil(total_items / self.per_page)

        return PaginationMeta(
            total_pages=total_pages,
            total_items=total_items,
            prev_page=(
                f"{prefix_url}?page={self.page - 1}&per_page={self.per_page}"
                if self.page > 1
                else None
            ),
            next_page=(
                f"{prefix_url}?page={self.page + 1}&per_page={self.per_page}"
                if self.page < total_pages
                else None
            ),
        )
