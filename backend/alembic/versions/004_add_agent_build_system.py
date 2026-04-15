"""add_agent_build_system

Revision ID: 004
Revises: 003
Create Date: 2025-10-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, Sequence[str], None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add agent build system tables: agent_versions, agent_build_logs, agent_test_runs"""

    # Create agent_versions table
    op.create_table(
        'agent_versions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('spec', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('code_path', sa.String(), nullable=True),
        sa.Column(
            'build_status',
            sa.Enum('PENDING', 'BUILDING', 'BUILT', 'TESTING', 'READY', 'FAILED', 'DEPRECATED',
                   name='buildstatusenum'),
            nullable=False,
            server_default='PENDING'
        ),
        sa.Column('metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_versions_id'), 'agent_versions', ['id'], unique=False)
    op.create_index(op.f('ix_agent_versions_agent_id'), 'agent_versions', ['agent_id'], unique=False)

    # Create agent_build_logs table
    op.create_table(
        'agent_build_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('agent_version_id', sa.String(), nullable=False),
        sa.Column('stage', sa.String(), nullable=False),
        sa.Column('level', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['agent_version_id'], ['agent_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_build_logs_id'), 'agent_build_logs', ['id'], unique=False)
    op.create_index(op.f('ix_agent_build_logs_agent_version_id'), 'agent_build_logs', ['agent_version_id'], unique=False)
    op.create_index(op.f('ix_agent_build_logs_created_at'), 'agent_build_logs', ['created_at'], unique=False)

    # Create agent_test_runs table
    op.create_table(
        'agent_test_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('agent_version_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('report', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_version_id'], ['agent_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_test_runs_id'), 'agent_test_runs', ['id'], unique=False)
    op.create_index(op.f('ix_agent_test_runs_agent_version_id'), 'agent_test_runs', ['agent_version_id'], unique=False)


def downgrade() -> None:
    """Remove agent build system tables"""

    # Drop tables in reverse order
    op.drop_index(op.f('ix_agent_test_runs_agent_version_id'), table_name='agent_test_runs')
    op.drop_index(op.f('ix_agent_test_runs_id'), table_name='agent_test_runs')
    op.drop_table('agent_test_runs')

    op.drop_index(op.f('ix_agent_build_logs_created_at'), table_name='agent_build_logs')
    op.drop_index(op.f('ix_agent_build_logs_agent_version_id'), table_name='agent_build_logs')
    op.drop_index(op.f('ix_agent_build_logs_id'), table_name='agent_build_logs')
    op.drop_table('agent_build_logs')

    op.drop_index(op.f('ix_agent_versions_agent_id'), table_name='agent_versions')
    op.drop_index(op.f('ix_agent_versions_id'), table_name='agent_versions')
    op.drop_table('agent_versions')

    # Drop enum type
    op.execute('DROP TYPE buildstatusenum')
