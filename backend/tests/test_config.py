"""Settings that need more than reading a value."""

from app.config import Settings


def test_neons_connection_string_works_as_pasted():
    neon = "postgresql://bb:secret@ep-x.eu-central-1.aws.neon.tech/bb?sslmode=require&channel_binding=require"
    assert Settings(database_url=neon).database_url == (
        "postgresql+asyncpg://bb:secret@ep-x.eu-central-1.aws.neon.tech/bb?ssl=require"
    )


def test_a_local_url_is_left_alone():
    local = "postgresql+asyncpg://bb:bb@localhost:5432/bookmark_brain"
    assert Settings(database_url=local).database_url == local
