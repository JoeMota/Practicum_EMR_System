import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_default_database_matches_compose():
    assert Settings.model_fields["DATABASE_URL"].default == "postgresql+asyncpg://emr:emr@localhost:5432/emr"
    settings = Settings(DATABASE_URL="postgresql+asyncpg://emr:emr@localhost:5432/emr")
    assert settings.SYNC_DATABASE_URL == "postgresql+psycopg2://emr:emr@localhost:5432/emr"
    assert settings.database_ssl is False


def test_render_url_becomes_asyncpg_with_ssl():
    settings = Settings(
        DATABASE_URL="postgres://emr:secret@dpg-abc.oregon-postgres.render.com:5432/emr?sslmode=require"
    )
    assert settings.DATABASE_URL == (
        "postgresql+asyncpg://emr:secret@dpg-abc.oregon-postgres.render.com:5432/emr"
    )
    assert settings.database_ssl is True
    assert settings.SYNC_DATABASE_URL == (
        "postgresql+psycopg2://emr:secret@dpg-abc.oregon-postgres.render.com:5432/emr?sslmode=require"
    )


def test_psycopg2_url_is_rewritten_for_the_app():
    settings = Settings(DATABASE_URL="postgresql+psycopg2://emr:emr@localhost:5432/emr")
    assert settings.DATABASE_URL.startswith("postgresql+asyncpg://")
    assert settings.SYNC_DATABASE_URL.startswith("postgresql+psycopg2://")


def test_production_rejects_placeholder_secret():
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production", JWT_SECRET_KEY="change-me")


def test_production_accepts_a_real_secret():
    settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="a-real-secret-value",
        NOTE_CONTENT_KEY="a-real-note-key",
    )
    assert settings.JWT_SECRET_KEY == "a-real-secret-value"
    assert settings.NOTE_CONTENT_KEY == "a-real-note-key"


def test_production_rejects_a_missing_note_key():
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production", JWT_SECRET_KEY="a-real-secret-value", NOTE_CONTENT_KEY="")
