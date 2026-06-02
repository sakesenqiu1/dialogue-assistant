from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_sqlite():
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "analyses" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("analyses")}
        with engine.begin() as conn:
            if "personalized_reasons" not in cols:
                conn.execute(
                    text("ALTER TABLE analyses ADD COLUMN personalized_reasons TEXT")
                )
            if "profile_tip" not in cols:
                conn.execute(text("ALTER TABLE analyses ADD COLUMN profile_tip TEXT"))
    if "conversations" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("conversations")}
        with engine.begin() as conn:
            if "user_narrative" not in cols:
                conn.execute(
                    text("ALTER TABLE conversations ADD COLUMN user_narrative TEXT")
                )


def init_db():
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite()
