"""
Adding columns account_id, http_forward, http_forward_address, key_id, remote_port to table sessions.

Revision ID: 1f5354d0e38f
Revises: None
Create Date: 2014-09-15 12:31:10.359964

"""

# revision identifiers, used by Alembic.
revision = '1f5354d0e38f'
down_revision = None

from alembic import op
import sqlalchemy as sa

from manager import dbhandler
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker


class OpenportSessionTmp(dbhandler.Base):
    __tablename__ = 'sessions'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    server = Column(String(50))
    remote_port = Column(Integer)
    session_token = Column(String(50))
    local_port = Column(Integer)
    pid = Column(Integer)
    active = Column(Boolean)
    restart_command = Column(String(200))
    account_id = Column(Integer)
    key_id = Column(Integer)
    http_forward = Column(Boolean)
    http_forward_address = Column(String(50))

    # In old format
    server_port = Column(String(50))


def upgrade():
    op.add_column('sessions', sa.Column('account_id', sa.Integer(), nullable=True))
    op.add_column('sessions', sa.Column('http_forward', sa.Boolean(), nullable=True))
    op.add_column('sessions', sa.Column('http_forward_address', sa.String(length=50), nullable=True))
    op.add_column('sessions', sa.Column('key_id', sa.Integer(), nullable=True))
    op.add_column('sessions', sa.Column('remote_port', sa.Integer(), nullable=True))

#    dbhandler.Base.metadata.bind = op.get_bind()

    session = sessionmaker(bind=op.get_bind())()
    for item in session.query(OpenportSessionTmp).all():
        item.remote_port = item.server_port

    session.commit()


# SQLite cannot drop columns!!!
#    op.drop_column('sessions', 'server_port')



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
