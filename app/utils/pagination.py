import math

from app.schemas.common import PaginatedResponse


def paginate(items, total: int, page: int, limit: int, schema) -> PaginatedResponse:
    total_pages = math.ceil(total / limit) if limit else 0
    return PaginatedResponse(
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        items=[schema.model_validate(item) for item in items],
    )
