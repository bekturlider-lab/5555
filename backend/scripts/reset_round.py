import argparse
import secrets
from bootstrap import ROOT, admin_environment
from seed_demo import seed, save_credentials

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Восстановление учебного банка. Затрагивает все банковские операции.")
    p.add_argument("--confirm", required=True, help="Введите RESET-CAMPUS-BANK")
    p.add_argument("--output", default=str(ROOT / ".private" / "client-access-new.csv"))
    args = p.parse_args()
    if args.confirm != "RESET-CAMPUS-BANK":
        p.error("Неверное подтверждение")
    admin_environment()
    from sqlalchemy import text, delete, select
    from app.db import SessionLocal, MAINTENANCE_LOCK
    from app.models import *
    from app.core.audit import audit
    with SessionLocal.begin() as db:
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": MAINTENANCE_LOCK})
        for model in [AiConversation, ProductOrder, LedgerEntry, BankTransaction, TransferIntent, Message, Ticket, Notification, RecoveryRequest, Session]:
            db.execute(delete(model))
        db.execute(delete(Provider))
        db.execute(delete(Account))
        db.execute(delete(User).where(User.is_demo.is_(True)))
        for client in db.scalars(select(User).where(User.role == "client", User.is_demo.is_(False))):
            db.add(Account(user_id=client.id, reference="CB" + secrets.token_hex(5).upper(), name="Основной счёт", kind="current", balance=0))
        rows = seed(db)
        audit(db, None, "operator.round_reset", clients=len(rows))
    save_credentials(rows, args.output)
    print("Раунд восстановлен. Новые доступы: " + args.output)
