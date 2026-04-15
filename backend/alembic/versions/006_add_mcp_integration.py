"""add mcp integration

Revision ID: 006
Revises: 005
Create Date: 2025-01-22

Adds Model Context Protocol (MCP) integration tables:
- mcp_server_configs: Configuration for external MCP servers
- agent_mcp_bindings: Many-to-many relationship between agents and MCP servers
- mcp_tool_executions: Audit trail of MCP tool invocations
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema for MCP integration"""

    # Create mcp_server_configs table
    op.create_table(
        "mcp_server_configs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column(
            "transport",
            sa.Enum("STDIO", "STREAMABLE_HTTP", "SSE", "WEBSOCKET", name="mcp_transport_type"),
            nullable=False,
        ),
        sa.Column("connection_config", JSON, nullable=False),  # Transport-specific config
        sa.Column("is_enabled", sa.Integer(), nullable=False, default=1),  # SQLite compat
        sa.Column(
            "requires_approval", sa.Integer(), nullable=False, default=0
        ),  # SQLite compat
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        op.f("ix_mcp_server_configs_name"), "mcp_server_configs", ["name"], unique=True
    )
    op.create_index(
        op.f("ix_mcp_server_configs_is_enabled"), "mcp_server_configs", ["is_enabled"]
    )

    # Create agent_mcp_bindings table (many-to-many)
    op.create_table(
        "agent_mcp_bindings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column(
            "server_id", sa.String(), sa.ForeignKey("mcp_server_configs.id"), nullable=False
        ),
        sa.Column(
            "config_overrides", JSON, nullable=True
        ),  # Agent-specific server config overrides
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_mcp_bindings_agent_id"), "agent_mcp_bindings", ["agent_id"])
    op.create_index(
        op.f("ix_agent_mcp_bindings_server_id"), "agent_mcp_bindings", ["server_id"]
    )
    # Create unique constraint for agent-server pair
    op.create_index(
        op.f("ix_agent_mcp_bindings_unique"),
        "agent_mcp_bindings",
        ["agent_id", "server_id"],
        unique=True,
    )

    # Create mcp_tool_executions table (audit log)
    op.create_table(
        "mcp_tool_executions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("server_name", sa.String(100), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("parameters", JSON, nullable=True),
        sa.Column("result", JSON, nullable=True),
        sa.Column("status", sa.String(20), nullable=False),  # "success", "error", "timeout"
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mcp_tool_executions_agent_id"), "mcp_tool_executions", ["agent_id"]
    )
    op.create_index(op.f("ix_mcp_tool_executions_user_id"), "mcp_tool_executions", ["user_id"])
    op.create_index(
        op.f("ix_mcp_tool_executions_server_name"), "mcp_tool_executions", ["server_name"]
    )
    op.create_index(
        op.f("ix_mcp_tool_executions_tool_name"), "mcp_tool_executions", ["tool_name"]
    )
    op.create_index(
        op.f("ix_mcp_tool_executions_timestamp"), "mcp_tool_executions", ["timestamp"]
    )
    op.create_index(op.f("ix_mcp_tool_executions_status"), "mcp_tool_executions", ["status"])


def downgrade() -> None:
    """Rollback MCP integration tables"""

    # Drop tables in reverse order
    op.drop_index(op.f("ix_mcp_tool_executions_status"), table_name="mcp_tool_executions")
    op.drop_index(op.f("ix_mcp_tool_executions_timestamp"), table_name="mcp_tool_executions")
    op.drop_index(op.f("ix_mcp_tool_executions_tool_name"), table_name="mcp_tool_executions")
    op.drop_index(op.f("ix_mcp_tool_executions_server_name"), table_name="mcp_tool_executions")
    op.drop_index(op.f("ix_mcp_tool_executions_user_id"), table_name="mcp_tool_executions")
    op.drop_index(op.f("ix_mcp_tool_executions_agent_id"), table_name="mcp_tool_executions")
    op.drop_table("mcp_tool_executions")

    op.drop_index(op.f("ix_agent_mcp_bindings_unique"), table_name="agent_mcp_bindings")
    op.drop_index(op.f("ix_agent_mcp_bindings_server_id"), table_name="agent_mcp_bindings")
    op.drop_index(op.f("ix_agent_mcp_bindings_agent_id"), table_name="agent_mcp_bindings")
    op.drop_table("agent_mcp_bindings")

    op.drop_index(op.f("ix_mcp_server_configs_is_enabled"), table_name="mcp_server_configs")
    op.drop_index(op.f("ix_mcp_server_configs_name"), table_name="mcp_server_configs")
    op.drop_table("mcp_server_configs")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS mcp_transport_type")
