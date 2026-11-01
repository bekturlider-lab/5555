"""Initial schema."""
from alembic import op
from app.db import Base
from app import models
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None
def upgrade():
    Base.metadata.create_all(bind=op.get_bind(), tables=[t for n,t in Base.metadata.tables.items() if n not in {"product_orders", "consent_receipts", "consent_acceptances", "ai_conversations"}])
def downgrade():
    Base.metadata.drop_all(bind=op.get_bind(), tables=[t for n,t in Base.metadata.tables.items() if n not in {"product_orders", "consent_receipts", "consent_acceptances", "ai_conversations"}])
