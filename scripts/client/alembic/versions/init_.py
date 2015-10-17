"""
Creating table sessions.

Revision ID: init
Revises: None
Create Date: 2014-09-15 12:31:10.359964

"""

# revision identifiers, used by Alembic.
revision = 'init'
down_revision = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('server', sa.String(50)),
        sa.Column('remote_port', sa.Integer),
        sa.Column('session_token', sa.String(50)),
        sa.Column('local_port', sa.Integer),
        sa.Column('pid', sa.Integer),
        sa.Column('active', sa.Boolean),
        sa.Column('restart_command', sa.String(200)),
        sa.Column('account_id', sa.Integer(), nullable=True),
        sa.Column('http_forward', sa.Boolean()),
        sa.Column('http_forward_address', sa.String(length=50), nullable=True),
        sa.Column('key_id', sa.Integer(), nullable=True),
    )

def downgrade():
    op.drop_table('sessions')