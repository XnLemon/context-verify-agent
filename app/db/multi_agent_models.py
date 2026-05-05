from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, JSON


try:
    from sqlalchemy.orm import DeclarativeBase
    class Base(DeclarativeBase):
        pass
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()


class AgentOutputRecord(Base):
    __tablename__ = "agent_outputs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(String(64), nullable=False, index=True)
    contract_id = Column(String(128), nullable=False, index=True)
    agent_id = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="completed")
    output_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<AgentOutputRecord(pipeline={self.pipeline_id}, agent={self.agent_id}, status={self.status})>"
