from bootstrap import ROOT, admin_environment
admin_environment()
from alembic import command
from alembic.config import Config

if __name__ == "__main__":
    command.upgrade(Config(str(ROOT / "backend" / "alembic.ini")), "head")
    print("Миграции применены.")
