import argparse
import json
from bootstrap import ROOT, admin_environment

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", default=str(ROOT / ".private" / "round-export.json"))
    args = p.parse_args()
    admin_environment()
    from sqlalchemy import select
    from app.db import SessionLocal
    from app.models import Account, BankTransaction, LedgerEntry, AuditEvent
    from pathlib import Path
    data = {}
    with SessionLocal() as db:
        for model in [Account, BankTransaction, LedgerEntry, AuditEvent]:
            data[model.__tablename__] = [{c.name: getattr(row, c.name) for c in model.__table__.columns} for row in db.scalars(select(model))]
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, default=str, indent=2))
    path.chmod(0o600)
    print("Состояние и аудит выгружены в " + str(path))
