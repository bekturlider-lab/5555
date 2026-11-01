"""Delete expired AI chats; never deletes tickets, accounts or consent receipts."""
from datetime import timedelta
from bootstrap import admin_environment

if __name__ == "__main__":
    admin_environment()
    from sqlalchemy import delete
    from app.db import SessionLocal
    from app.models import AiConversation
    from app.models.identity import now
    with SessionLocal.begin() as db:
        result = db.execute(delete(AiConversation).where(AiConversation.updated_at < now() - timedelta(days=7)))
    print("Удалено устаревших AI-чатов: " + str(result.rowcount))
