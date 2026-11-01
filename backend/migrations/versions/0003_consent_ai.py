"""Versioned agreements and private AI support conversations."""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("consent_receipts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("documents", sa.JSON(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ai_consent", sa.Boolean(), nullable=False),
        sa.Column("ai_changed_at", sa.DateTime(timezone=True)))
    op.create_table("consent_acceptances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("receipt_id", sa.String(36), sa.ForeignKey("consent_receipts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("ai_conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("receipt_id", sa.String(36), sa.ForeignKey("consent_receipts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("messages", sa.JSON(), nullable=False),
        sa.Column("pending_key", sa.String(80)),
        sa.Column("pending_at", sa.DateTime(timezone=True)),
        sa.Column("escalation_reason", sa.String(40), nullable=False),
        sa.Column("ticket_id", sa.String(36), sa.ForeignKey("tickets.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, index=True))


def downgrade():
    op.drop_table("ai_conversations")
    op.drop_table("consent_acceptances")
    op.drop_table("consent_receipts")
