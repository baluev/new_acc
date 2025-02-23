"""Initial migration

Revision ID: initial_migration
Revises: 
Create Date: 2024-03-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'initial_migration'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # This is an empty migration since we created the database using create_db.py
    pass


def downgrade():
    # This is an empty migration since we created the database using create_db.py
    pass 