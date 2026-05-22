"""add mcp provider table

Revision ID: 1d6f0a9e2c44
Revises: b1c2d3e4f5a6
Create Date: 2026-05-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "1d6f0a9e2c44"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mcp_provider",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("account_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("label", sa.String(length=255), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("icon", sa.String(length=512), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''::text")),
        sa.Column("category", sa.String(length=255), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("transport", sa.String(length=255), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("url", sa.String(length=1024), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("command", sa.String(length=1024), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("headers", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("tool_names", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("args", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("env", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default=sa.text("30")),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source_type", sa.String(length=255), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("source_key", sa.String(length=255), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("source_url", sa.String(length=1024), nullable=False, server_default=sa.text("''::character varying")),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(0)"), server_onupdate=sa.text("CURRENT_TIMESTAMP(0)")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(0)")),
        sa.PrimaryKeyConstraint("id", name="pk_mcp_provider_id"),
    )
    op.create_index("mcp_provider_account_id_idx", "mcp_provider", ["account_id"])
    op.create_index("mcp_provider_is_public_idx", "mcp_provider", ["is_public"])
    op.create_index("mcp_provider_source_type_idx", "mcp_provider", ["source_type"])
    op.create_index("mcp_provider_category_idx", "mcp_provider", ["category"])
    op.create_foreign_key(None, "mcp_provider", "account", ["account_id"], ["id"])


def downgrade():
    op.drop_constraint(None, "mcp_provider", type_="foreignkey")
    op.drop_index("mcp_provider_category_idx", table_name="mcp_provider")
    op.drop_index("mcp_provider_source_type_idx", table_name="mcp_provider")
    op.drop_index("mcp_provider_is_public_idx", table_name="mcp_provider")
    op.drop_index("mcp_provider_account_id_idx", table_name="mcp_provider")
    op.drop_table("mcp_provider")
