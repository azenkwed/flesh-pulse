import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/flesh_pulse",
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    from backend.database.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # tsvector column for full-text search
        await conn.execute(text(
            "ALTER TABLE articles ADD COLUMN IF NOT EXISTS search_vector tsvector"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_articles_search ON articles USING GIN(search_vector)"
        ))
        await conn.execute(text("""
            CREATE OR REPLACE FUNCTION update_articles_search_vector()
            RETURNS TRIGGER AS $$
            BEGIN
              NEW.search_vector := to_tsvector('english',
                coalesce(NEW.title, '') || ' ' ||
                coalesce(NEW.description, '') || ' ' ||
                coalesce(NEW.ai_summary, '') || ' ' ||
                coalesce(NEW.tags::text, '')
              );
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        await conn.execute(text("""
            DO $$ BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'articles_search_vector_update'
              ) THEN
                CREATE TRIGGER articles_search_vector_update
                  BEFORE INSERT OR UPDATE ON articles
                  FOR EACH ROW EXECUTE FUNCTION update_articles_search_vector();
              END IF;
            END $$;
        """))
        await conn.execute(text("""
            UPDATE articles
            SET search_vector = to_tsvector('english',
                coalesce(title, '') || ' ' ||
                coalesce(description, '') || ' ' ||
                coalesce(ai_summary, '') || ' ' ||
                coalesce(tags::text, '')
            )
            WHERE search_vector IS NULL
        """))


async def get_db():
    async with SessionLocal() as session:
        yield session
