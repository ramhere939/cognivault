"""
SQLAlchemy database setup.
Uses aiosqlite for async operations with SQLite.
FTS5 virtual table created for hybrid keyword search.
"""
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event, text


class Base(DeclarativeBase):
    pass


# Engine and session factory — initialized on startup
engine = None
async_session_factory = None


async def init_db(sqlite_path: str):
    """Initialize database, create tables, and enable FTS5."""
    global engine, async_session_factory

    Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite+aiosqlite:///{sqlite_path}"

    engine = create_async_engine(
        db_url,
        echo=False,
        connect_args={"check_same_thread": False, "timeout": 30.0},
    )

    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Import models so Base knows about them
    from app.models import document, chunk, entity, relationship, alert  # noqa

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Enable WAL mode for better concurrent read performance
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        # Create FTS5 virtual table for hybrid keyword search
        await conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
            USING fts5(
                chunk_id UNINDEXED,
                doc_id UNINDEXED,
                content,
                tokenize='porter ascii'
            )
        """))


async def get_db() -> AsyncSession:
    """FastAPI dependency: yield a database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db():
    """Shutdown: dispose connection pool."""
    global engine
    if engine:
        await engine.dispose()
