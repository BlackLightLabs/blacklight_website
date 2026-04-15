"""add_prompt_templates_and_version_diffs

Revision ID: 005
Revises: 004
Create Date: 2025-10-22 06:30:00.000000

Adds prompt template management and version comparison capabilities:
- prompt_templates table for versioned, editable prompts
- agent_version_diffs table for tracking changes between versions
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, Sequence[str], None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add prompt templates and version diff tables"""

    # Create prompt_templates table
    op.create_table(
        'prompt_templates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column(
            'template_type',
            sa.Enum('SYSTEM', 'USER', 'AGENT', 'REVISION', name='prompttemplatetype'),
            nullable=False,
            server_default='SYSTEM'
        ),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('variables', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_prompt_templates_id'), 'prompt_templates', ['id'], unique=False)
    op.create_index(op.f('ix_prompt_templates_name'), 'prompt_templates', ['name'], unique=True)
    op.create_index(op.f('ix_prompt_templates_template_type'), 'prompt_templates', ['template_type'], unique=False)
    op.create_index(op.f('ix_prompt_templates_created_at'), 'prompt_templates', ['created_at'], unique=False)

    # Create agent_version_diffs table
    op.create_table(
        'agent_version_diffs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('from_version_id', sa.String(), nullable=False),
        sa.Column('to_version_id', sa.String(), nullable=False),
        sa.Column('diff_type', sa.String(50), nullable=False),
        sa.Column('changes', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['from_version_id'], ['agent_versions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_version_id'], ['agent_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_version_diffs_id'), 'agent_version_diffs', ['id'], unique=False)
    op.create_index(op.f('ix_agent_version_diffs_from_version_id'), 'agent_version_diffs', ['from_version_id'], unique=False)
    op.create_index(op.f('ix_agent_version_diffs_to_version_id'), 'agent_version_diffs', ['to_version_id'], unique=False)
    op.create_index(op.f('ix_agent_version_diffs_created_at'), 'agent_version_diffs', ['created_at'], unique=False)


def downgrade() -> None:
    """Remove prompt templates and version diff tables"""

    # Drop agent_version_diffs table
    op.drop_index(op.f('ix_agent_version_diffs_created_at'), table_name='agent_version_diffs')
    op.drop_index(op.f('ix_agent_version_diffs_to_version_id'), table_name='agent_version_diffs')
    op.drop_index(op.f('ix_agent_version_diffs_from_version_id'), table_name='agent_version_diffs')
    op.drop_index(op.f('ix_agent_version_diffs_id'), table_name='agent_version_diffs')
    op.drop_table('agent_version_diffs')

    # Drop prompt_templates table
    op.drop_index(op.f('ix_prompt_templates_created_at'), table_name='prompt_templates')
    op.drop_index(op.f('ix_prompt_templates_template_type'), table_name='prompt_templates')
    op.drop_index(op.f('ix_prompt_templates_name'), table_name='prompt_templates')
    op.drop_index(op.f('ix_prompt_templates_id'), table_name='prompt_templates')
    op.drop_table('prompt_templates')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS prompttemplatetype')
