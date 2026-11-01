"""Add customer product applications to existing installations."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("product_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("reference", sa.String(30), nullable=False, unique=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_id", sa.String(30), nullable=False),
        sa.Column("request_key", sa.String(80), nullable=False),
        sa.Column("note", sa.String(1000), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("staff_note", sa.String(1000), nullable=False),
        sa.Column("fulfilled_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "request_key"),
        sa.CheckConstraint("status IN ('new','in_review','completed','declined','cancelled')"))


def downgrade():
    op.drop_table("product_orders")
