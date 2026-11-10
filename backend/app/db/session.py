from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

url = make_url(settings.database_url)
connect_args = {"check_same_thread": False} if url.drivername.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_agricultural_documents() -> None:
    """Add RAG metadata columns to existing Phase 1 SQLite databases."""
    inspector = inspect(engine)
    if "agricultural_documents" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("agricultural_documents")}
    additions = {
        "crop": "VARCHAR(100)",
        "topic": "VARCHAR(100)",
        "source_name": "VARCHAR(200)",
        "source_url": "VARCHAR(1000)",
    }
    with engine.begin() as connection:
        for name, type_ in additions.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE agricultural_documents ADD COLUMN {name} {type_}"))


def migrate_farmer_columns(target_engine=engine) -> None:
    """Add nullable profile fields to existing Phase 1 farmer tables safely."""
    if not target_engine.dialect.name == "sqlite":
        return
    inspector = inspect(target_engine)
    if "farmers" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("farmers")}
    additions = {
        "district": "VARCHAR(120)",
        "land_area_acres": "FLOAT",
    }
    with target_engine.begin() as connection:
        for name, type_ in additions.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE farmers ADD COLUMN {name} {type_}"))


def migrate_message_request_id(target_engine=engine) -> None:
    """Add the idempotency key used to make assistant retries safe."""
    if target_engine.dialect.name != "sqlite":
        return
    inspector = inspect(target_engine)
    if "messages" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("messages")}
    with target_engine.begin() as connection:
        if "request_id" not in existing:
            connection.execute(text("ALTER TABLE messages ADD COLUMN request_id VARCHAR(64)"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_messages_request_id ON messages (request_id)"))
