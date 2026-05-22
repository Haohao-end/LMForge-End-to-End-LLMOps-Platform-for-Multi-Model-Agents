from datetime import UTC, datetime
import uuid

from sqlalchemy import (
    Column,
    UUID,
    String,
    Text,
    DateTime,
    Boolean,
    Integer,
    text,
    PrimaryKeyConstraint,
    Index,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from internal.extension.database_extension import db


def _utcnow_naive() -> datetime:
    """返回无时区的 UTC 时间，兼容数据库 DateTime 列且避免 utcnow 退化警告。"""
    return datetime.now(UTC).replace(tzinfo=None)


class McpProvider(db.Model):
    """MCP 提供者模型"""
    __tablename__ = "mcp_provider"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_mcp_provider_id"),
        Index("mcp_provider_account_id_idx", "account_id"),
        Index("mcp_provider_is_public_idx", "is_public"),
        Index("mcp_provider_source_type_idx", "source_type"),
        Index("mcp_provider_category_idx", "category"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    account_id = Column(UUID, ForeignKey("account.id"), nullable=True)
    name = Column(String(255), nullable=False, server_default=text("''::character varying"))
    label = Column(String(255), nullable=False, server_default=text("''::character varying"))
    icon = Column(String(512), nullable=False, server_default=text("''::character varying"))
    description = Column(Text, nullable=False, server_default=text("''::text"))
    category = Column(String(255), nullable=False, server_default=text("''::character varying"))
    transport = Column(String(255), nullable=False, server_default=text("''::character varying"))
    url = Column(String(1024), nullable=False, server_default=text("''::character varying"))
    command = Column(String(1024), nullable=False, server_default=text("''::character varying"))
    headers = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    tool_names = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    args = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    env = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    timeout_seconds = Column(Integer, nullable=False, server_default=text("30"))
    is_public = Column(Boolean, nullable=False, server_default=text("false"))
    source_type = Column(String(255), nullable=False, server_default=text("''::character varying"))
    source_key = Column(String(255), nullable=False, server_default=text("''::character varying"))
    source_url = Column(String(1024), nullable=False, server_default=text("''::character varying"))
    published_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(0)"),
        server_onupdate=text("CURRENT_TIMESTAMP(0)"),
        default=_utcnow_naive,
    )
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP(0)"))

    account = relationship("Account", foreign_keys=[account_id], lazy="joined")

