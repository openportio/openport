"""
Adding columns account_id, http_forward, http_forward_address, key_id, remote_port to table sessions.

Revision ID: 1f5354d0e38f
Revises: None
Create Date: 2014-09-15 12:31:10.359964

"""

# revision identifiers, used by Alembic.
revision = '1f5354d0e38f'
down_revision = 'init'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker


def upgrade():
    op.add_column('sessions', sa.Column('account_id', sa.Integer(), nullable=True))
    op.add_column('sessions', sa.Column('http_forward', sa.Boolean(), nullable=True))
    op.add_column('sessions', sa.Column('http_forward_address', sa.String(length=50), nullable=True))
    op.add_column('sessions', sa.Column('key_id', sa.Integer(), nullable=True))


def downgrade():
    op.add_column('sessions', sa.Column('server_port', sa.Integer(), nullable=True))

    session = sessionmaker(bind=op.get_bind())()
    for item in session.query(OpenportSessionTmp).all():
        item.server_port = item.remote_port

    session.commit()

 #    op.drop_column('sessions', 'remote_port')

 #   op.drop_column('sessions', 'key_id')
 #   op.drop_column('sessions', 'http_forward_address')
 #   op.drop_column('sessions', 'http_forward')
 #   op.drop_column('sessions', 'account_id')
