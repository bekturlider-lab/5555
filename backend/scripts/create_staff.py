import argparse
from bootstrap import ROOT, admin_environment
from seed_demo import create_staff, save_credentials

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--username", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--role", choices=["admin", "staff"], default="staff")
    p.add_argument("--output", default=str(ROOT / ".private" / "staff-access.csv"))
    args = p.parse_args()
    if not args.username.replace("_", "").isalnum() or not 3 <= len(args.username) <= 40:
        p.error("Логин: 3–40 латинских букв, цифр или _")
    admin_environment()
    from app.db import SessionLocal
    with SessionLocal.begin() as db:
        row = create_staff(db, args.username.lower(), args.name, args.role)
    if row:
        save_credentials([row], args.output)
        print("Сотрудник создан. Доступ сохранён в " + args.output)
    else:
        print("Такой сотрудник уже существует. Пароль не изменён.")
