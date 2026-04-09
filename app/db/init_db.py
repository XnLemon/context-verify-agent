from sqlalchemy import text

from app.db.models import Base
from app.db.session import get_engine


def ensure_postgres_schema() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_doc_version "
                "ON knowledge_chunks (doc_id, version)"
            )
        )
