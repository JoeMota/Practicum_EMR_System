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

### UTEP login + Duo

Production sign-in is **Sign in with UTEP** (Microsoft Entra ID / campus SSO). UTEP already runs **Duo MFA** on that login, so this app does not re-prompt Duo after SSO.

1. Ask UTEP IT (or an Entra admin) to register a **Web** application:
   - Redirect URI: `{API_PUBLIC_URL}/api/v1/auth/sso/callback` (local example: `http://localhost:8000/api/v1/auth/sso/callback`)
   - Allow accounts in the UTEP tenant only
2. Put `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET` in `backend/.env`
3. Set `FRONTEND_URL` to the SPA origin and `CORS_ORIGINS` to match
4. For campus-only login, set `AUTH_REQUIRE_UTEP_SSO=true` (hides demo password MFA)
5. Users must still be on the course roster (email `@utep.edu` / `@miners.utep.edu`); SSO alone does not create EMR accounts

Check what the UI will offer: `GET /api/v1/auth/providers`.

### Bring-your-own Duo (team / personal Duo, not UTEP campus)

You can use **your own Duo Admin account** so the password login path pushes a real Duo prompt to your phone (no UTEP IT required). This replaces the educational `123456` code.

1. Create a Duo account / trial at [duo.com](https://duo.com) and open the **Duo Admin Panel**.
2. **Users → Add** a user whose **username is the exact EMR email** (e.g. `jamota@miners.utep.edu`), then enroll that user’s phone (Duo Mobile push or SMS).
3. **Applications → Protect an Application → Duo Web SDK** (Universal Prompt).  
   Set the app’s **Redirect URI** to:  
   `http://localhost:8000/api/v1/auth/duo/callback`  
   (use your public API URL in deployed environments).
4. Copy into `backend/.env`:

```bash
DUO_CLIENT_ID=<Client ID from the Web SDK app>
DUO_CLIENT_SECRET=<Client secret>
DUO_API_HOSTNAME=<API hostname, e.g. api-xxxxxxxx.duosecurity.com>
DUO_REDIRECT_URI=http://localhost:8000/api/v1/auth/duo/callback
FRONTEND_URL=http://localhost:5173
```

5. Restart the API. `GET /api/v1/auth/providers` should show `"duo": true`.
6. Sign in with email + password → UI says **Continue to Duo** → approve on your phone → back into the EMR.

Username in Duo **must match** the EMR login email. Leave `ENTRA_*` empty if you are not using campus SSO yet.

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
| UTEP SSO / Duo | `GET /auth/providers`, `/auth/sso/login`, `/auth/sso/callback`, `/auth/duo/callback` |
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

## Deploy (Vercel — frontend)

The UI is a Vite SPA under `frontend/`. FastAPI + Postgres are **not** hosted on Vercel; run the API elsewhere (Railway, Render, Fly.io, a VM, etc.) or use mock mode for UI-only previews.

### Recommended project settings

1. Import the GitHub repo in Vercel (or `cd frontend && vercel link`).
2. Set **Root Directory** to `frontend` (uses `frontend/vercel.json`).
3. Framework preset: **Vite** (build `npm run build`, output `dist`).
4. Environment variables:

| Variable | Preview / Production | Notes |
|----------|----------------------|--------|
| `VITE_API_URL` | API origin, e.g. `https://api.example.com` | Baked at build time. No trailing slash. Required for live API. |
| `VITE_USE_MOCK` | `false` (default) or `true` | `true` = in-memory demo UI with no backend. |

5. On the **backend** host, set `CORS_ORIGINS` to include your Vercel URL(s), e.g. `["https://your-app.vercel.app"]`.

Preview deploys: push a non-production branch after Git is connected. Production: promote a preview or deploy to `main` / `--prod`.

CLI (from `frontend/`, after `vercel login` or `VERCEL_TOKEN`):

```bash
cd frontend
vercel link --yes
vercel env add VITE_API_URL
vercel deploy          # preview
vercel deploy --prod   # production
```

Without a hosted API, a UI-only preview can set `VITE_USE_MOCK=true` for that deployment’s build env.

## Important

Do not commit `.env` files, passwords, API keys, or real patient information.
