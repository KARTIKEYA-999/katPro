import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.config import DATABASE_URL, BASE_DIR

logger = logging.getLogger("sih_procurement.database")

# Create PostgreSQL SQLAlchemy Engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI dependency for yielding database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initializes PostgreSQL database and verifies connection.
    If database tables are missing, applies schema.sql and seed.sql automatically.
    """
    try:
        with engine.connect() as conn:
            # Check if users table exists
            result = conn.execute(text("SELECT to_regclass('public.users');")).scalar()
            if not result:
                logger.warning("Database tables not found. Applying database/schema.sql and seed.sql...")
                schema_path = BASE_DIR / "database" / "schema.sql"
                seed_path = BASE_DIR / "database" / "seed.sql"

                if schema_path.exists():
                    with open(schema_path, "r", encoding="utf-8") as f:
                        conn.execute(text(f.read()))
                        conn.commit()
                    logger.info("Successfully executed schema.sql")

                if seed_path.exists():
                    with open(seed_path, "r", encoding="utf-8") as f:
                        conn.execute(text(f.read()))
                        conn.commit()
                    logger.info("Successfully executed seed.sql")
            else:
                logger.info("PostgreSQL database connection verified and schema is present.")
    except Exception as e:
        logger.error(f"Error initializing or verifying database: {e}")
        raise
