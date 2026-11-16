"""Create student authentication table."""
from alembic import op
import sqlalchemy as sa

revision = "003_create_students_table"
down_revision = "002_create_document_chunks_fts"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "students",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_students_email", "students", ["email"], unique=True)

def downgrade():
    op.drop_index("ix_students_email", table_name="students")
    op.drop_table("students")
