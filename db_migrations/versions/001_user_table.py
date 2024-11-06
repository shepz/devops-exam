"""user table

Revision ID: 001
Revises:
Create Date: 2020-04-10 13:26:35.383652

"""
from alembic import op
from sqlalchemy import Column, DateTime, Integer, String, func

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user",
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("email", String, nullable=False, unique=True),
        Column("name", String, nullable=False),
        Column(
            "created_at",
            DateTime(timezone=True),
            server_default=func.current_timestamp(),
        ),
    )


def downgrade():
    op.drop_table("user")
