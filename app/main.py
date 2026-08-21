import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import Base, engine
from app import models  
from app.utils.rate_limit import rate_limit_middleware

from app.routes import (
    auth, destinations, packages, itinerary, customers, travelers,
    bookings, hotels, activities, guides, payments, reviews, dashboard,
    reports, ws,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("travel_platform")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured (create_all). For production, prefer Alembic migrations.")
    yield



app = FastAPI(
    title=settings.APP_NAME,
    description="A complete Travel & Tour Operations Management Platform API.",
    version="1.0.0",
    lifespan=lifespan,
)

origins = ["*"] if settings.CORS_ORIGINS == "*" else [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(rate_limit_middleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": jsonable_encoder(exc.errors())},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning("Database integrity error: %s", str(exc.orig))
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "A database integrity constraint was violated."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception while processing %s %s", request.method, request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred."},
    )


_routers = [
    auth.router, destinations.router, packages.router, itinerary.router,
    customers.router, travelers.router, bookings.router, hotels.router,
    activities.router, guides.router, payments.router, reviews.router,
    dashboard.router, reports.router, ws.router,
]

for _router in _routers:
    app.include_router(_router)

api_v1 = APIRouter(prefix="/api/v1")
for _router in _routers:
    api_v1.include_router(_router)
app.include_router(api_v1, include_in_schema=False)  # avoid doubling every path in /docs


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
