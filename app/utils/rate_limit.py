import time
from collections import defaultdict, deque

from fastapi import Request, HTTPException, status

from app.config import settings

_hits: dict[str, deque] = defaultdict(deque)


async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    limit = settings.RATE_LIMIT_REQUESTS

    bucket = _hits[client_ip]
    while bucket and now - bucket[0] > window:
        bucket.popleft()

    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )

    bucket.append(now)
    response = await call_next(request)
    return response
