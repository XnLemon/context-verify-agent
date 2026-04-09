from sqlalchemy import text

from app.db.models import Base
from app.db.session import get_engine


def ensure_postgres_schema() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE chat_threads DROP CONSTRAINT IF EXISTS chat_threads_contract_id_key"))
        conn.execute(text("ALTER TABLE chat_threads ADD COLUMN IF NOT EXISTS member_id INTEGER NOT NULL DEFAULT 0"))
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_chat_threads_contract_member "
                "ON chat_threads (contract_id, member_id)"
            )
        )

        conn.execute(text("ALTER TABLE history_logs ADD COLUMN IF NOT EXISTS member_id INTEGER NOT NULL DEFAULT 0"))
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_history_logs_contract_member_created_at "
                "ON history_logs (contract_id, member_id, created_at DESC)"
            )
        )
