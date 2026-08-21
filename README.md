# Travel & Tour Operations Management Platform

A FastAPI backend for managing tour packages, destinations, bookings, travelers,
hotel reservations, activities, guides, payments, cancellations/refunds, reviews,
and operational reporting.

Built as a layered application (routes → services → repositories/models) with
JWT auth, role-based access control, and a full pytest suite that exercises the
real business rules end-to-end.

## Tech stack

Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2.0 (ORM) · SQLite (default) /
PostgreSQL · JWT (python-jose) · Passlib/bcrypt · Alembic · Uvicorn · Pytest

## Quick start (SQLite, zero setup)

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # defaults already point at SQLite

uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs** for interactive Swagger UI (every endpoint,
try-it-out included), or **/redoc** for ReDoc.

Tables are created automatically on startup via `Base.metadata.create_all`
for convenience. For anything beyond local development, use Alembic instead
(see below) — `create_all` cannot handle schema changes to existing tables.

## Running with PostgreSQL

```bash
export DATABASE_URL="postgresql+psycopg2://travel_user:travel_pass@localhost:5432/travel_db"
pip install psycopg2-binary
alembic upgrade head
uvicorn app.main:app --reload
```

## Docker

```bash
docker compose up --build
```

This starts Postgres + the API together, runs Alembic migrations
automatically, and serves the API on `http://localhost:8000`.

## Database migrations (Alembic)

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

An initial migration (`alembic/versions/e07e9314432c_initial_schema.py`) is
already included and has been verified to build the full schema from empty.

## Running the tests

```bash
pytest -v
```

43 tests covering auth/RBAC, destinations, packages, the full booking
lifecycle (overbooking prevention, duplicate-booking rules, slot
management), payments, the cancellation/refund engine's four day-based
tiers, review eligibility rules, and the bonus features (API versioning,
PDF/QR/Excel export, WebSocket live status, caching, Celery) — all run
against an isolated in-memory SQLite database per test, hitting the real
HTTP layer through FastAPI's `TestClient`.

A `smoke_test.sh` script is also included, which boots a real server and
drives the entire flow (register → login → destination → package →
booking → payment → hotel reservation → guide assignment → cancellation
→ review) through actual `curl` calls, asserting the correct HTTP status
code for every business rule. Run it with `bash smoke_test.sh`.

`smoke_test_bonus.sh` does the same for the bonus features — including a
real WebSocket client that opens a connection, triggers a payment over
HTTP, and asserts the live status push arrives. Run it with
`bash smoke_test_bonus.sh`.

## Project structure

```
app/
├── main.py            # App wiring: routers, CORS, rate limiting, exception handlers
├── config.py           # Settings (env-driven via pydantic-settings)
├── database.py          # SQLAlchemy engine/session/Base
├── models/              # SQLAlchemy ORM models (one file per entity)
├── schemas/              # Pydantic request/response schemas + validation
├── routes/                # FastAPI routers — thin, delegate to services
├── services/               # Business logic: booking, payment, cancellation/
│                             refund engine, guide/hotel rules, reviews, dashboard
├── repositories/            # Generic CRUDBase (get/list/create/update/soft-delete)
├── auth/                     # Password hashing, JWT issuing/verification, RBAC deps
└── utils/                     # Pagination helper, custom HTTP exceptions, rate limiter
tests/                          # Pytest suite (isolated in-memory DB per test)
alembic/                        # Migration environment + initial schema migration
```

Routes stay thin and call into `services/`, which hold the actual business
rules (slot math, refund tiers, overlap detection, etc.) and talk to the
database through SQLAlchemy sessions / the generic repository base class.
This keeps each layer independently testable and matches the separation
requested in the spec (Level 15).

## Auth & roles

Register via `POST /auth/register`, log in via `POST /auth/login` to get a
JWT `access_token` + `refresh_token`, then pass `Authorization: Bearer
<access_token>` on subsequent requests. Five roles exist —
`super_admin`, `tour_manager`, `booking_agent`, `customer`, `tour_guide` —
enforced per-endpoint via dependency guards (`require_admin`,
`require_management`, `require_operations` in `app/auth/dependencies.py`).
Adjust which roles can hit which endpoints there if your org chart differs.

## Notable business rules implemented

- **Packages**: end date after start date, capacity > 0, available slots
  never exceed capacity, cancelled/completed packages reject new bookings.
- **Itinerary**: day numbers unique per package, end time after start time,
  day number can't exceed the package's `duration_days`.
- **Bookings**: overbooking prevention, one active (Pending/Confirmed)
  booking per customer per package, automatic `total_amount = base_amount +
  tax - discount`. Slots are only decremented on **confirmation** (i.e. once
  payment covers the full amount) and restored on cancellation — see
  `app/services/booking_service.py`.
- **Payments**: duplicate `transaction_id` rejected, payment amount capped
  at the outstanding booking balance, a payment that fully covers the
  balance auto-confirms the booking, refunds capped at the paid (and
  not-yet-refunded) amount.
- **Cancellation & Refund Engine** (`app/services/cancellation_service.py`):
  refund % is computed from days remaining before `package.start_date` —
  15+ days → 90%, 7–14 → 70%, 2–6 → 40%, <2 → 0% — applied against
  successful payments oldest-first, with a full `Cancellation` history
  record. Two cancel endpoints exist on purpose (see below).
- **Hotels**: overlapping reservations on the same room are rejected, room
  capacity × number_of_rooms must cover the travelers on the booking.
- **Guides**: inactive guides can't be assigned, and a guide can't be
  assigned to two tours with overlapping date ranges.
- **Reviews**: only bookings with status `Completed` are reviewable, one
  review per booking, rating constrained to 1–5 at both the schema and DB
  (`CheckConstraint`) level.

### Why there are two "cancel booking" endpoints

The spec lists both `PUT /bookings/{id}/cancel` (Level 6) and
`POST /bookings/{booking_id}/cancel` (Level 10) at what reads like the same
path — but they're different HTTP methods on purpose, and different
implementations, kept deliberately distinct rather than merged into one:

- `PUT /bookings/{id}/cancel` — the plain Level 6 cancellation: marks the
  booking cancelled and restores package slots. No refund math.
- `POST /bookings/{booking_id}/cancel` — the full Level 10 refund engine:
  computes and applies the tiered refund, restores slots, and creates a
  `Cancellation` history record.

## What's implemented vs. simplified

Fully implemented: Levels 1–12 (auth, destinations, packages, itinerary,
customers/travelers, bookings, hotels/rooms/reservations,
activities/guides, payments, cancellation & refund engine, reviews, and
search/filter/pagination across the relevant list endpoints), plus a real
layered architecture (Level 15) and the core of security/data-integrity
(Level 16: JWT, RBAC, hashing, request validation, FK/unique/check
constraints, soft delete, global exception handlers, a lightweight
in-memory rate limiter, CORS) and DB/performance basics (Level 17:
indexes on searchable/filterable columns, Alembic migrations, session
management via a per-request dependency).

Simplified by design, given this is a learning/reference project rather
than a production deployment:

- **Notifications (Level 13)** are simulated: `app/services/notification_service.py`
  logs each notification and persists it to a `notifications` table via
  FastAPI `BackgroundTasks`, instead of calling a real email/SMS provider.
  Swap in a real provider there when you have one.
- **Audit logs** (`app/models/audit_log.py`) exist as a table/model but
  aren't yet wired into every write endpoint — add a call per action you
  want tracked.
- **Rate limiting** is a small in-memory sliding window
  (`app/utils/rate_limit.py`), fine for a single process; swap for
  Redis-backed limiting behind multiple workers.

## Bonus features

All implemented and covered by tests (`tests/test_bonus_features.py`),
not just scaffolded:

- **API versioning** — every route is mounted both at its original path
  and under `/api/v1/...` (e.g. `/auth/login` and `/api/v1/auth/login`
  both work identically). New integrations should prefer `/api/v1`; a
  future breaking change would ship as `/api/v2` alongside it.
- **PDF booking confirmations** — `GET /bookings/{id}/confirmation-pdf`
  returns a generated PDF (reportlab) with the booking details and an
  embedded QR code.
- **QR codes** — `GET /bookings/{id}/qr-code` returns a standalone PNG QR
  code encoding a booking reference.
- **Excel report export** — `GET /dashboard/reports/export` returns a
  6-sheet `.xlsx` workbook (Summary, Popular Destinations, Popular
  Packages, Package Performance, Destination Revenue, Cancellations) built
  with openpyxl.
- **WebSocket live booking status** — connect to
  `ws://host/ws/bookings/{id}` to get the booking's current status
  immediately on connect, then a live push every time it changes (payment
  confirms it, it's cancelled, etc.). Broadcasts are wired in from the
  payment and cancellation endpoints via FastAPI `BackgroundTasks`.
- **Caching** — `app/services/cache_service.py` is Redis-backed when
  `REDIS_URL` is set and reachable, and transparently falls back to an
  in-memory TTL cache otherwise. Applied to `GET /dashboard/summary`
  (30s TTL by default, invalidated on booking/payment/cancellation writes).
- **Celery scheduled jobs** — `app/celery_app.py` + `app/tasks.py` define
  a daily-at-08:00-UTC task (`send_upcoming_tour_reminders`) via Celery
  beat. With no `CELERY_BROKER_URL` configured it runs in-process
  (`task_always_eager=True`), so the task logic is directly testable
  without any broker — see `test_celery_task_runs_eagerly_without_broker`.
  Point `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` at a real Redis/RabbitMQ
  instance and run `celery -A app.celery_app worker` +
  `celery -A app.celery_app beat` as separate processes for production;
  `docker-compose.yml` has commented-out service definitions for both.
- **Docker & Docker Compose** — `Dockerfile` + `docker-compose.yml` (API +
  Postgres + Redis, with optional Celery worker/beat services).

Not implemented: email integration (would replace the simulated
notification service with a real provider — SendGrid, SES, etc.).

## Example walkthrough

```bash
# Register + log in
curl -X POST localhost:8000/auth/register -H "Content-Type: application/json" \
  -d '{"name":"Admin","email":"admin@travel.com","password":"AdminPass123","role":"super_admin"}'
TOKEN=$(curl -X POST localhost:8000/auth/login -H "Content-Type: application/json" \
  -d '{"email":"admin@travel.com","password":"AdminPass123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Create a destination + package, then book it
curl -X POST localhost:8000/destinations -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"name":"Manali","country":"India"}'
# ...see smoke_test.sh for the full end-to-end flow.
```
