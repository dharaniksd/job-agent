"""create initial tables

Revision ID: 0001
Revises: 
Create Date: 2024-01-01
"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('linkedin_id', sa.String(), nullable=True),
        sa.Column('linkedin_access_token', sa.String(), nullable=True),
        sa.Column('linkedin_profile_url', sa.String(), nullable=True),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('email_notifications', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('linkedin_id'),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table(
        'resumes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('filename', sa.String(), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('parsed_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('company', sa.String(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('match_score', sa.Float(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url'),
    )

    op.create_table(
        'applications',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('job_id', sa.String(), sa.ForeignKey('jobs.id'), nullable=True),
        sa.Column('resume_id', sa.String(), sa.ForeignKey('resumes.id'), nullable=True),
        sa.Column('status', sa.Enum('pending', 'in_progress', 'awaiting_review', 'submitted', 'failed',
                                    name='applicationstatus'), nullable=True),
        sa.Column('form_data', sa.JSON(), nullable=True),
        sa.Column('pending_questions', sa.JSON(), nullable=True),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('applications')
    op.drop_table('jobs')
    op.drop_table('resumes')
    op.drop_index('ix_users_email', 'users')
    op.drop_table('users')
