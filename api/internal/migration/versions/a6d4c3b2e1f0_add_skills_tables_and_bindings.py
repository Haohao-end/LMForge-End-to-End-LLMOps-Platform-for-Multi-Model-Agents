"""add skill package tables and skills bindings

Revision ID: a6d4c3b2e1f0
Revises: 1d6f0a9e2c44, c8d9e0f1a2b3
Create Date: 2026-05-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "a6d4c3b2e1f0"
down_revision = ("1d6f0a9e2c44", "c8d9e0f1a2b3")
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("app_config", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "skills",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            )
        )

    with op.batch_alter_table("app_config_version", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "skills",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            )
        )

    op.create_table(
        "skill_package",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("source_key", sa.String(length=255), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("source_path", sa.String(length=1024), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("label", sa.String(length=255), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("icon", sa.String(length=1024), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''::text")),
        sa.Column("category", sa.String(length=255), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("executor_type", sa.String(length=64), nullable=False, server_default=sa.text("'scf'::character varying")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("latest_source_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("source_checksum", sa.String(length=128), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("sync_status", sa.String(length=64), nullable=False, server_default=sa.text("'pending'::character varying")),
        sa.Column("sync_error", sa.Text(), nullable=False, server_default=sa.text("''::text")),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP(0)"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP(0)"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(0)")),
        sa.PrimaryKeyConstraint("id", name="pk_skill_package_id"),
        sa.UniqueConstraint("source_key", name="uq_skill_package_source_key"),
    )
    op.create_index("skill_package_source_key_idx", "skill_package", ["source_key"], unique=False)
    op.create_index("skill_package_category_idx", "skill_package", ["category"], unique=False)
    op.create_index("skill_package_enabled_idx", "skill_package", ["enabled"], unique=False)
    op.create_index("skill_package_current_version_idx", "skill_package", ["current_version"], unique=False)

    op.create_table(
        "skill_package_version",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("skill_package_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("bundle", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("checksum", sa.String(length=128), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("sync_status", sa.String(length=64), nullable=False, server_default=sa.text("'pending'::character varying")),
        sa.Column("sync_error", sa.Text(), nullable=False, server_default=sa.text("''::text")),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP(0)"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP(0)"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(0)")),
        sa.ForeignKeyConstraint(["skill_package_id"], ["skill_package.id"], name="fk_skill_package_version_skill_package_id"),
        sa.PrimaryKeyConstraint("id", name="pk_skill_package_version_id"),
        sa.UniqueConstraint("skill_package_id", "version", name="uq_skill_package_version_package_version"),
    )
    op.create_index(
        "skill_package_version_skill_package_id_idx",
        "skill_package_version",
        ["skill_package_id"],
        unique=False,
    )
    op.create_index(
        "skill_package_version_version_idx",
        "skill_package_version",
        ["version"],
        unique=False,
    )
    op.create_index(
        "skill_package_version_sync_status_idx",
        "skill_package_version",
        ["sync_status"],
        unique=False,
    )


def downgrade():
    op.drop_index("skill_package_version_sync_status_idx", table_name="skill_package_version")
    op.drop_index("skill_package_version_version_idx", table_name="skill_package_version")
    op.drop_index("skill_package_version_skill_package_id_idx", table_name="skill_package_version")
    op.drop_table("skill_package_version")

    op.drop_index("skill_package_current_version_idx", table_name="skill_package")
    op.drop_index("skill_package_enabled_idx", table_name="skill_package")
    op.drop_index("skill_package_category_idx", table_name="skill_package")
    op.drop_index("skill_package_source_key_idx", table_name="skill_package")
    op.drop_table("skill_package")

    with op.batch_alter_table("app_config_version", schema=None) as batch_op:
        batch_op.drop_column("skills")

    with op.batch_alter_table("app_config", schema=None) as batch_op:
        batch_op.drop_column("skills")
