"""Local preview only. Production always uses an externally configured PostgreSQL."""
import os
import secrets
import subprocess
from bootstrap import ROOT

if __name__ == "__main__":
    private = ROOT / ".private"
    private.mkdir(exist_ok=True)
    secret_file = private / "app-secret"
    if not secret_file.exists():
        secret_file.write_text(secrets.token_urlsafe(48))
        secret_file.chmod(0o600)
    os.environ.setdefault("APP_SECRET", secret_file.read_text().strip())
    os.environ.setdefault("APP_ENV", "preview")
    os.environ.setdefault("ALLOWED_HOSTS", "*")
    os.environ.setdefault("DEMO_QUICK_LOGIN", "true")
    os.environ.setdefault("COOKIE_SECURE", "false")
    pg = None
    if not os.environ.get("DATABASE_URL"):
        import pgserver
        pg = pgserver.get_server(ROOT / ".pgdata", cleanup_mode="stop")
        os.environ["DATABASE_URL"] = pg.get_uri()
    from alembic import command
    from alembic.config import Config
    command.upgrade(Config(str(ROOT / "backend" / "alembic.ini")), "head")
    from app.db import SessionLocal
    from seed_demo import seed, create_staff, save_credentials
    with SessionLocal.begin() as db:
        rows = seed(db)
        for username, name, role in [("admin", "Администратор B bank", "admin"), ("support", "Александра · Поддержка", "staff")]:
            row = create_staff(db, username, name, role)
            if row:
                rows.append(row)
    if rows:
        save_credentials(rows, private / "demo-access.csv")
    print("Учебный банк готов. Индивидуальные доступы: .private/demo-access.csv", flush=True)
    subprocess.run([str(ROOT / ".venv" / "bin" / "python") if (ROOT / ".venv" / "bin" / "python").exists() else os.sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", str(ROOT / "backend"), "--host", "0.0.0.0", "--port", os.environ.get("PORT", "8000"), "--no-proxy-headers"], check=True)
