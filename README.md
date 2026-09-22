# Practicum EMR System

Educational Electronic Medical Record (EMR) for UTEP Health Sciences practicum (CS 5389).

Stack matches the Week 0 tech recommendation: **React + TypeScript + Vite + MUI** → **FastAPI REST** → **PostgreSQL** (SQLAlchemy + Alembic), with Docker Compose for local Postgres.

## Architecture

```text
Browser  →  React (Vite :5173)  →  /api/v1/* (proxy)  →  FastAPI (:8000)  →  PostgreSQL (:5432)
```

The frontend `src/api/*` modules call the live API by default. Set `VITE_USE_MOCK=true` to fall back to the in-memory demo without a backend.

## Project layout

```text
├── frontend/          React + MUI UI
├── backend/           FastAPI + SQLAlchemy + Alembic
├── docker-compose.yml Postgres 16
├── .env.example
└── README.md
```

## First-time setup

```bash
git clone https://github.com/JoeMota/Practicum_EMR_System.git
cd Practicum_EMR_System
cp .env.example .env
cp backend/.env.example backend/.env
```

### Database

```bash
docker compose up -d
```

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m app.scripts.seed --demo  # RBAC + synthetic courses/patients
```

### Frontend

```bash
cd frontend
npm install
```

## Run locally

**Terminal 1 — API**

```bash
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000  
- OpenAPI: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

**Terminal 2 — UI**

```bash
cd frontend && npm run dev
```

- App: http://localhost:5173 (Vite proxies `/api` → `:8000`)

## Demo logins (after `--demo` seed)

| Role | Email | Password | MFA |
|------|-------|----------|-----|
| Student | `daniel.reyes@miners.utep.edu` | `practicum1` | `123456` |
| Student | `clarissa.dominguez@miners.utep.edu` | `practicum1` | `123456` |
| Instructor / Admin | `gerardo.sillas@utep.edu` | `practicum1` | `123456` |
| Instructor | `joe.mota@utep.edu` | `practicum1` | `123456` |

All patients are synthetic training data — never commit real PHI.

## API surface (v1)

| Area | Endpoints |
|------|-----------|
| Auth / MFA | `POST /auth/challenge`, `/auth/send-code`, `/auth/verify-code`, `/auth/login`, `GET /auth/me`, `POST /auth/change-password` |
| Courses | `GET /courses`, `/courses/{id}`, `/courses/{id}/instructors` |
| Roster | `GET/POST/DELETE /courses/{id}/roster…` |
| Patients | `GET /patients`, `GET/PATCH /patients/{id}…`, `POST …/reset` |
| Notes | CRUD + `sign` / `cosign` / `return` / `addendum` / `review-queue` |
| Audit | `GET /audit` |
| Scheduling | appointments + referrals |

## Tests

```bash
cd backend && source .venv/bin/activate && pytest
```

## Important

Do not commit `.env` files, passwords, API keys, or real patient information.
