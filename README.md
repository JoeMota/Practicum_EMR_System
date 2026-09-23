# Practicum EMR System

Educational Electronic Medical Record (EMR) for UTEP Health Sciences practicum (CS 5389).

Stack matches the Week 0 tech recommendation: **React + TypeScript + Vite + MUI** → **FastAPI REST** → **PostgreSQL** (SQLAlchemy + Alembic), with Docker Compose for local Postgres.

## Architecture

```text
Browser  →  React (Vite :5173)  →  /api/v1/* (proxy)  →  FastAPI (:8000)  →  PostgreSQL (:5432)
```

The frontend `src/api/*` modules call the live API by default. Set `VITE_USE_MOCK=true` to fall back to the in-memory demo without a backend.

Inpatient workflows stay a **Phase 2 stub** (`frontend/src/features/inpatient/`).

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

Prefer Docker Compose:

```bash
docker compose up -d
```

Or use a local Postgres with:

```text
DATABASE_URL=postgresql+asyncpg://emr:emr@localhost:5432/emr
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
| Student | `sam.torres@miners.utep.edu` | `practicum1` | `123456` |
| Instructor / Admin | `gerardo.sillas@utep.edu` | `practicum1` | `123456` |
| Instructor | `joe.mota@utep.edu` | `practicum1` | `123456` |

All seeded accounts use password **`practicum1`** and MFA code **`123456`** (dev only).

Roster-imported students get temporary password **`ChangeMe1!`** and are forced through **Change password** on first login (`must_change_password`).

All patients are synthetic training data — never commit real PHI.

### JWT notes

- After MFA verify (or Swagger password login), the API returns a Bearer **JWT** (`access_token`).
- The browser stores it in session storage and sends `Authorization: Bearer …` on `/api/v1/*`.
- Tokens expire per `JWT` settings in `backend/.env` (`JWT_SECRET_KEY`, algorithm HS256). Change the secret before any shared deploy.
- A `401` from the API clears the session and returns you to login; users with a temp password are redirected to **Change password** before clinical screens.

## Demo script (Phase 1 MVP)

Open http://localhost:5173 after both servers are running and the DB is seeded.

### 1. Daniel — student path (write & sign)

1. Login: `daniel.reyes@miners.utep.edu` / `practicum1`
2. MFA: choose email (or SMS), enter `123456`
3. Select **PHAR 5320** as **student**
4. Open **patients** — you should see practice patient Rosa Villalobos and your assessment case Albert Einstein (`TR-10057-DR`)
5. Open Einstein → **Notes** → start a Pharmacy MTM note (or continue a draft)
6. Fill sections, pick instructor **Gerardo Sillas** as reviewer, **Sign / submit**
7. Note status becomes **pending review**

### 2. Gerardo — instructor review (Sam’s seeded note + Daniel)

1. Log out; login: `gerardo.sillas@utep.edu` / `practicum1` / MFA `123456`
2. Select **PHAR 5320** as **instructor** (or admin)
3. Open **Review queue** — Sam Torres already has a pending note; Daniel’s appears after step 1
4. Open a note → **Co-sign** (optional comment) or **Return** with revision feedback
5. As admin you can also open **Roster** and **Audit**

### 3. Joe — second instructor path

1. Login: `joe.mota@utep.edu` / `practicum1` / MFA `123456`
2. Instructor role on PHAR 5320
3. Review queue includes Clarissa’s seeded pending note (routed to Joe)
4. Co-sign or return

### 4. Sam — pre-submitted student

1. Login: `sam.torres@miners.utep.edu` / `practicum1` / MFA `123456`
2. Student on PHAR 5320 — own Einstein case (`TR-10057-ST`) with a note already pending with Gerardo

### 5. Roster temp password (optional)

1. As Gerardo (admin), open **Roster** → import a CSV row
2. New account password is **`ChangeMe1!`** until they complete **Change password**

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

`?role=` on patients/notes is checked against the caller’s **course enrollments** (spoofing `instructor` as a student returns 403).

## Tests

```bash
cd backend && source .venv/bin/activate && pytest
```

Includes MFA → patients smoke and notes draft → sign → cosign/return.

## Important

Do not commit `.env` files, passwords, API keys, or real patient information.
