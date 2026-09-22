from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.api.routes import audit, auth, courses, notes, patients, roster, scheduling

app = FastAPI(title=settings.PROJECT_NAME, version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=prefix)
app.include_router(courses.router, prefix=prefix)
app.include_router(roster.router, prefix=prefix)
app.include_router(patients.router, prefix=prefix)
app.include_router(notes.router, prefix=prefix)
app.include_router(audit.router, prefix=prefix)
app.include_router(scheduling.router, prefix=prefix)


@app.get("/")
async def root():
    return {"message": "UTEP Educational EHR API is running", "docs": "/docs"}


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "healthy", "database": "connected"}
