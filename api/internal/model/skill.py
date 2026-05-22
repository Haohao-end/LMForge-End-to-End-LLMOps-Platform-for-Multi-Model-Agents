from __future__ import annotations

from datetime import UTC, datetime
import uuid

from sqlalchemy import (
    Column,
    UUID,
    String,
    Text,
    Integer,
    DateTime,
    Boolean,
    PrimaryKeyConstraint,
    Index,
    ForeignKey,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from internal.extension.database_extension import db


def _utcnow_naive() -> datetime:
    """返回无时区的 UTC 时间，兼容数据库 DateTime 列。"""
    return datetime.now(UTC).replace(tzinfo=None)


class SkillPackage(db.Model):
    """技能包基础信息。"""

    __tablename__ = "skill_package"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_skill_package_id"),
        UniqueConstraint("source_key", name="uq_skill_package_source_key"),
        Index("skill_package_source_key_idx", "source_key"),
        Index("skill_package_category_idx", "category"),
        Index("skill_package_enabled_idx", "enabled"),
        Index("skill_package_current_version_idx", "current_version"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    source_key = Column(String(255), nullable=False, server_default=text("''::character varying"))
    source_path = Column(String(1024), nullable=False, server_default=text("''::character varying"))
    name = Column(String(255), nullable=False, server_default=text("''::character varying"))
    label = Column(String(255), nullable=False, server_default=text("''::character varying"))
    icon = Column(String(1024), nullable=False, server_default=text("''::character varying"))
    description = Column(Text, nullable=False, server_default=text("''::text"))
    category = Column(String(255), nullable=False, server_default=text("''::character varying"))
    tags = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    capabilities = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    executor_type = Column(String(64), nullable=False, server_default=text("'scf'::character varying"))
    enabled = Column(Boolean, nullable=False, server_default=text("true"))
    current_version = Column(Integer, nullable=False, server_default=text("1"))
    latest_source_version = Column(Integer, nullable=False, server_default=text("1"))
    source_checksum = Column(String(128), nullable=False, server_default=text("''::character varying"))
    sync_status = Column(String(64), nullable=False, server_default=text("'pending'::character varying"))
    sync_error = Column(Text, nullable=False, server_default=text("''::text"))
    published_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(0)"),
        server_onupdate=text("CURRENT_TIMESTAMP(0)"),
        default=_utcnow_naive,
    )
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP(0)"))

    versions = relationship(
        "SkillPackageVersion",
        back_populates="skill_package",
        lazy="selectin",
        order_by=lambda: SkillPackageVersion.version.desc(),
    )


class SkillPackageVersion(db.Model):
    """技能包版本历史表。"""

    __tablename__ = "skill_package_version"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_skill_package_version_id"),
        UniqueConstraint("skill_package_id", "version", name="uq_skill_package_version_package_version"),
        Index("skill_package_version_skill_package_id_idx", "skill_package_id"),
        Index("skill_package_version_version_idx", "version"),
        Index("skill_package_version_sync_status_idx", "sync_status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    skill_package_id = Column(UUID, ForeignKey("skill_package.id"), nullable=False)
    version = Column(Integer, nullable=False, server_default=text("1"))
    manifest = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    bundle = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    checksum = Column(String(128), nullable=False, server_default=text("''::character varying"))
    sync_status = Column(String(64), nullable=False, server_default=text("'pending'::character varying"))
    sync_error = Column(Text, nullable=False, server_default=text("''::text"))
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(0)"),
        server_onupdate=text("CURRENT_TIMESTAMP(0)"),
        default=_utcnow_naive,
    )
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP(0)"))

    skill_package = relationship("SkillPackage", back_populates="versions", lazy="joined")
