import csv
import json
import secrets
import random
import os
from pathlib import Path
from datetime import timedelta
from bootstrap import ROOT, admin_environment


def save_credentials(rows, output):
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["username", "password", "full_name", "role"])
        writer.writeheader()
        writer.writerows(rows)
    path.chmod(0o600)


def create_staff(db, username, full_name, role):
    from sqlalchemy import select
    from app.models import User
    from app.core.security import hash_password
    existing = db.scalar(select(User).where(User.username == username))
    if existing:
        return None
    password = YOUR_VALUE_HERE
    user = User(username=username, full_name=full_name, role=role, email=username + "@bbank.test", password_hash=YOUR_VALUE_HERE
    db.add(user)
    db.flush()
    return {"username": username, "password": password, "full_name": full_name, "role": role}


def seed(db):
    from sqlalchemy import select
    from app.models import User, Account, Card, Provider, Ticket, Message, Notification
    from app.models.identity import now
    from app.core.security import hash_password
    from app.services.ledger import post
    if db.scalar(select(User.id).where(User.is_demo.is_(True)).limit(1)):
        return []
    rng = random.Random(20261027)
    customers = json.loads((ROOT / "backend" / "fixtures" / "clients.json").read_text())
    services = json.loads((ROOT / "backend" / "fixtures" / "payment_providers.json").read_text())
    opening = db.scalar(select(Account).where(Account.reference == "SYSTEM-OPENING"))
    if not opening:
        opening = Account(reference="SYSTEM-OPENING", name="Начальный баланс", kind="system", balance=0)
        db.add(opening)
        db.flush()
    providers = []
    for p in services:
        provider = db.get(Provider, p['id'])
        if not provider:
            acc = Account(reference="SYS-" + p['id'].upper(), name=p['name'], kind="system")
            db.add(acc)
            db.flush()
            provider = Provider(**p, account_id=acc.id)
            db.add(provider)
            db.flush()
        providers.append(provider)
    users, primary, credentials = [], [], []
    for i, name in enumerate(customers, 1):
        password = YOUR_VALUE_HERE
        user = User(username=f"client{i:03d}", full_name=name, email=f"client{i:03d}@bbank.test", password_hash=YOUR_VALUE_HERE, is_demo=True)
        db.add(user)
        db.flush()
        current = Account(user_id=user.id, reference=f"CB{i:06d}", name="Основной счёт")
        savings = Account(user_id=user.id, reference=f"SV{i:06d}", name="На большие планы", kind="savings")
        db.add_all([current, savings])
        db.flush()
        card = Card(account_id=current.id, last4=f"{4100+i:04d}", color="graphite" if i % 3 else "yellow", status="frozen" if i % 11 == 0 else "active")
        db.add(card)
        db.flush()
        post(db, opening.id, current.id, (148650 if i == 1 else rng.randint(50000, 280000)) * 100, kind="opening", description="Начальный учебный баланс", category="Пополнения", stamp=now()-timedelta(days=35), send_notifications=False)
        post(db, opening.id, savings.id, (42500 if i == 1 else rng.randint(10000, 60000)) * 100, kind="opening", description="Начальный учебный баланс", category="Пополнения", stamp=now()-timedelta(days=35), send_notifications=False)
        for j, days in enumerate([23, 19, 14, 10, 6, 5, 4, 3, 2, 1, 0]):
            p = providers[(i + j) % len(providers)]
            amount = [390, 1290, 2450, 600, 850, 1490][(i+j) % 6] * 100
            post(db, current.id, p.account_id, amount, actor=user, kind="payment", description=p.name, category=p.category, customer_reference=f"SIM-{i:04d}", stamp=now()-timedelta(days=days, hours=j % 6), send_notifications=False)
        db.add(Notification(user_id=user.id, title="Добро пожаловать в B bank", body="Ваш личный кабинет готов. Все операции проводятся с учебными деньгами.", link="/bank/accounts"))
        users.append(user)
        primary.append(current)
        credentials.append({"username": user.username, "password": password, "full_name": name, "role": "client"})
    for i, user in enumerate(users):
        target = primary[(i+1) % len(primary)]
        post(db, primary[i].id, target.id, [1500, 3200, 750, 2100, 4900][i % 5] * 100, actor=user, description=["За совместный обед", "За учебные материалы", "Спасибо!", "На поездку", "Возврат перевода"][i % 5], stamp=now()-timedelta(days=i % 5, hours=1), send_notifications=False)
    for i in [0, 2, 5]:
        ticket = Ticket(user_id=users[i].id, title=["Как изменить лимит карты?", "Вопрос по переводу", "Нужна выписка за месяц"][[0,2,5].index(i)], category="Карты" if i == 0 else "Общий вопрос")
        db.add(ticket)
        db.flush()
        db.add(Message(ticket_id=ticket.id, author_id=users[i].id, body="Здравствуйте! Подскажите, пожалуйста, как это сделать в личном кабинете?"))
    db.flush()
    return credentials


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / ".private" / "client-access.csv"))
    args = parser.parse_args()
    admin_environment()
    from app.db import SessionLocal
    with SessionLocal.begin() as db:
        credentials = seed(db)
    if credentials:
        save_credentials(credentials, args.output)
        print(f"Создано {len(credentials)} клиентов. Доступы сохранены в {args.output}")
    else:
        print("Учебные клиенты уже существуют. Данные не изменены.")
