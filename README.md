# Practicum EMR System

Electronic Medical Record (EMR) system built as our practicum project.

## Tech Stack

**Frontend**
- React + TypeScript + Vite
- Material UI (MUI)

**Backend**
- Python + FastAPI
- REST API

**Database**
- PostgreSQL
- SQLAlchemy
- Alembic

**Development & Testing**
- Docker Compose
- Pytest (backend)
- GitHub Actions CI

**Deployment**
- Docker
- GitHub Actions
- Managed cloud services

## Features

- Students and instructors can use patient charts, write notes, create referrals, and review notes.
- Courses move from `planned` to `active`, from `active` to `ended`, and from `ended` to `archived`. Ended courses can return to `active`. Archived courses cannot reopen. Ended and archived courses reject changes to patients, notes, referrals and roster imports. Roster removal stays available so access can be removed after a course ends. Archived courses are hidden from non-admin course lists.
- The same course code can be used for different terms. Each code and term pair must be unique.
- The roster page has an Add people card with a single-person form and spreadsheet upload. Imports add students. Admins can also add instructors. Instructors can remove other instructors. They cannot remove themselves or the last instructor.
- Admins can create courses, manage course status and roster access, deactivate and reactivate accounts, review audit activity, and view course reports with CSV export.

## Roles

| Role | Capabilities |
| --- | --- |
| Student | Advance encounters, write and sign notes, and create referrals. |
| Instructor | Create patients, update patient status, reset practice charts, advance encounters, co-sign or return notes, create referrals, import student rosters, remove instructors, and view audit activity. Instructors must be rostered in a course to use course-scoped actions. They cannot remove themselves or the last instructor. |
| Admin | Create patients, update patient status, reset practice charts, import and remove course roster members, remove instructors, create courses, manage course status, add instructor access, manage user access, run reports, and view audit activity. Admins need instructor membership to use the Instructor role in a course. |

## API additions

All paths below are under `/api/v1`.

- `POST /courses` creates a course. Admin permission is required.
- `POST /courses/{course_id}/status` changes course status. Admin permission is required.
- `POST /courses/{course_id}/roster/import` imports rows with `role=student` or `role=instructor`. Only admins can add instructors.
- `DELETE /courses/{course_id}/roster/{user_id}?role=student|instructor` removes a course membership. Staff need roster-import permission. Instructor removal also needs instructor-remove permission. The endpoint blocks self-removal and removal of the last instructor.
- `PATCH /users/{user_id}/active` changes a user's active state. Admin permission is required.
- `GET /reports/courses/{course_id}?format=csv` returns a course report as CSV. Without `format=csv`, it returns JSON. Admin permission is required for both formats.

## Project Structure

```text
Practicum_EMR_System/
├── frontend/
├── backend/
├── docker-compose.yml
├── .env.example
└── README.md
```

## First-Time Setup

Clone the repository and enter the project:

```bash
git clone https://github.com/Gerardos0/Practicum_EMR_System.git
cd Practicum_EMR_System
```

### Frontend

```bash
cd frontend
npm install
cd ..
```

### Backend

```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cd ..
```

> Windows users can activate the virtual environment with:
>
> `.venv\Scripts\activate`

## Run the Project

### 1. Start the Database

From the repository folder:

```bash
docker compose up -d
```

### 2. Start the Backend

Open a terminal:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
python -m app.scripts.seed
uvicorn app.main:app --reload
```

The migration command applies all database migrations. The seed command creates demo data. In development, the seed password defaults to `practicum-demo`. Set `SEED_DEMO_PASSWORD` to use another value. The seeded sign-ins are:

- Student: `daniel.reyes@miners.utep.edu`
- Instructor: `joe.mota@utep.edu`
- Administrator (also an instructor in seeded courses): `gerardo.sillas@utep.edu`

Use the configured seed demo password for each account.

Backend:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

### 3. Start the Frontend

Open a second terminal:

```bash
cd frontend
npm run dev
```

Frontend:

```text
http://localhost:5173
```

## Daily Start

Once you've completed the first-time setup, you only need:

**Terminal 1**

```bash
docker compose up -d

cd backend
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload
```

**Terminal 2**

```bash
cd frontend
npm run dev
```

The default `docker compose up -d` starts the database. To run the API in Docker, use this command from the project folder:

```bash
docker compose --profile api up -d --build
docker compose exec api python -m app.scripts.seed
```

API:

```text
http://localhost:8000
```

The API container runs `alembic upgrade head` at startup. It does not seed demo data. Run the seed command separately when needed.

## Testing and CI

Backend tests use Pytest and a separate `emr_test` PostgreSQL database. The test setup creates that database when needed, applies migrations, and seeds demo data. Start the Compose database, then run:

```bash
cd backend
pytest -v
```

GitHub Actions runs backend `pytest -q` with PostgreSQL. It runs `npm ci` and `npm run build` for the frontend on pull requests and pushes to `master`. The repo has no frontend test files or test script. CI does not run lint.

## Known Limitations

- Courses cannot be deleted. Archive a course instead. Archived courses cannot reopen.
- Admin permissions do not grant instructor membership. To use Instructor mode for a course, an admin must also be rostered there as an instructor.
- The roster form and spreadsheet upload require a 9-digit 800 number. The API does not independently validate the format.

## Deploy

### API on Render

In Render, New → Blueprint, and pick this repo. Set `SEED_DEMO_PASSWORD` when it asks.

After the first deploy, open the service shell and run:

```bash
python -m app.scripts.seed
```

Copy the service URL. The database is the smallest paid Postgres plan. The free web service sleeps when idle.

### Frontend on Vercel

Import the repo. Root directory is `frontend`. Add `VITE_API_URL` and set it to the Render URL, with no trailing slash.

`https://*.vercel.app` is allowed. For another domain, set `CORS_ORIGINS` on the Render service.

## Important

Do not commit `.env` files, passwords, API keys, or real patient information to the repository.
