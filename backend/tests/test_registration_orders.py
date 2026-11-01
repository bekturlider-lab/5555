"""Integration checks. Use a dedicated disposable PostgreSQL test database only."""
import os
import sys
from pathlib import Path
from uuid import uuid4
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def bank():
    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("Set TEST_DATABASE_URL to a disposable PostgreSQL database")
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
    os.environ["APP_ENV"] = "test"
    os.environ["COOKIE_SECURE"] = "false"
    os.environ["ALLOWED_HOSTS"] = "testserver,localhost,127.0.0.1"
    os.environ["APP_SECRET"] = "only-for-disposable-integration-tests-campus-bank"
    from sqlalchemy import text
    from app.db import Base, engine
    from app import models
    from app.main import app
    from fastapi.testclient import TestClient
    names = ','.join('"' + t.name + '"' for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE " + names + " CASCADE"))
    with TestClient(app) as client:
        accept_terms(client)
        yield client, app
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE " + names + " CASCADE"))


def accept_terms(client):
    bundle = client.get('/api/v1/legal/status').json()
    response = client.post('/api/v1/legal/accept', json={"version": bundle['version'], "reviewed_documents": [d['id'] for d in bundle['documents']], "agree": True}, headers=headers(client))
    assert response.status_code == 200, response.text
    return bundle


def signup(client, username="example_user", **extra):
    return client.post('/api/v1/auth/register', json={"username": username, "full_name": "Учебный Пользователь", "email": username + "@campus.test", "password": "YOUR_VALUE_HERE", "accept_training_terms": True, **extra})


def headers(client):
    return {"X-CSRF-Token": client.cookies.get("campus_csrf", "")}


def request_order(client, product="black", key=None):
    return client.post('/api/v1/orders', json={"product_id": product, "note": "Учебная заявка", "request_key": key or str(uuid4())}, headers=headers(client))


def login_staff(app, role="staff"):
    from app.db import SessionLocal
    from app.models import User
    from app.core.security import hash_password
    from fastapi.testclient import TestClient
    with SessionLocal.begin() as db:
        db.add(User(username="employee", full_name="Сотрудник Тестовый", email="employee@campus.test", password_hash=hash_password("Employee-password-2026"), role=role))
    client = TestClient(app)
    accept_terms(client)
    response = client.post('/api/v1/auth/login', json={"username": "employee", "password": "YOUR_VALUE_HERE"})
    assert response.status_code == 200, response.text
    return client


def test_registration_creates_zero_account_and_persistent_session(bank):
    client, _ = bank
    response = signup(client)
    assert response.status_code == 201, response.text
    assert response.json()['role'] == 'client'
    assert 'password' not in response.text
    assert client.get('/api/v1/auth/me').json()['username'] == 'example_user'
    accounts = client.get('/api/v1/accounts').json()
    assert len(accounts) == 1 and accounts[0]['balance'] == 0
    assert client.get('/api/v1/dashboard').status_code == 200


def test_registration_rejects_role_injection_and_duplicate_login(bank):
    client, _ = bank
    assert signup(client, role='admin').status_code == 422
    assert signup(client, accept_training_terms=False).status_code == 400
    assert signup(client).status_code == 201
    assert signup(client, username="EXAMPLE_USER").status_code == 409


def test_order_requires_session_and_csrf(bank):
    client, _ = bank
    assert request_order(client).status_code == 401
    assert signup(client).status_code == 201
    assert client.post('/api/v1/orders', json={"product_id": "black", "request_key": str(uuid4())}).status_code == 403
    assert client.get('/api/v1/staff/orders').status_code == 403


def test_idempotent_order_and_customer_cancellation(bank):
    client, _ = bank
    assert signup(client).status_code == 201
    key = str(uuid4())
    first, second = request_order(client, key=key), request_order(client, key=key)
    assert first.status_code == 201, first.text
    assert first.json()['id'] == second.json()['id']
    assert len(client.get('/api/v1/orders').json()) == 1
    assert request_order(client, product='goals', key=key).status_code == 409
    order_id = first.json()['id']
    response = client.post('/api/v1/orders/'+order_id+'/cancel', json={}, headers=headers(client))
    assert response.json()['status'] == 'cancelled'
    assert client.post('/api/v1/orders/'+order_id+'/cancel', json={}, headers=headers(client)).status_code == 409


def test_other_customer_cannot_cancel_or_see_order(bank):
    client, _ = bank
    assert signup(client).status_code == 201
    order = request_order(client).json()
    assert client.post('/api/v1/auth/logout', json={}, headers=headers(client)).status_code == 200
    assert signup(client, username="different_user").status_code == 201
    assert client.get('/api/v1/orders').json() == []
    assert client.post('/api/v1/orders/'+order['id']+'/cancel', json={}, headers=headers(client)).status_code == 404


@pytest.mark.parametrize('product,resource', [('yellow','cards'), ('goals','accounts')])
def test_staff_completion_provisions_once(bank, product, resource):
    client, app = bank
    assert signup(client).status_code == 201
    order = request_order(client, product).json()
    before = len(client.get('/api/v1/'+resource).json())
    staff = login_staff(app)
    url = '/api/v1/staff/orders/'+order['id']
    update = {"status": "completed", "staff_note": "Готово"}
    response = staff.patch(url, json=update, headers=headers(staff))
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'completed'
    assert len(client.get('/api/v1/'+resource).json()) == before + 1
    if product == 'yellow':
        assert client.get('/api/v1/cards').json()[0]['label'] == 'B Yellow'
    assert staff.patch(url, json=update, headers=headers(staff)).status_code == 409
    assert len(client.get('/api/v1/'+resource).json()) == before + 1
    assert client.get('/api/v1/orders').json()[0]['staff_note'] == 'Готово'
    staff.close()


def test_public_content_and_images(bank):
    client, _ = bank
    content = client.get('/api/v1/public/content').json()
    assert len(content['products']) == 9
    assert content['fictional'] is True
    assert 'contacts' not in content
    assert '996220715205' not in str(content)
    assert '996995393911' not in str(content)
    for image in ['office','products','team']:
        response = client.get('/images/'+image+'.png')
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('image/')


def test_registration_statistics_require_staff_session(bank):
    client, app = bank
    assert client.get('/api/v1/staff/overview').status_code == 401
    assert signup(client).status_code == 201
    assert client.get('/api/v1/staff/overview').status_code == 403
    with login_staff(app, role='admin') as admin:
        response = admin.get('/api/v1/staff/overview')
        assert response.status_code == 200, response.text
        data = response.json()
        assert data['clients'] == data['registered_clients'] == data['registered_today'] == 1
        assert data['demo_clients'] == data['blocked'] == 0


def test_registration_statistics_separate_demo_profiles_and_refresh(bank):
    from datetime import timedelta
    from sqlalchemy import select
    from app.db import SessionLocal
    from app.models import User
    from app.core.money import day_start
    client, app = bank
    assert signup(client).status_code == 201
    with SessionLocal.begin() as db:
        password_hash = YOUR_VALUE_HERE == 'example_user'))
        db.add(User(username='older_client', full_name='Другой Клиент', email='older@campus.test', password_hash=password_hash, status='blocked', created_at=day_start()-timedelta(days=1)))
        db.add(User(username='another_admin', full_name='Администратор', email='admin@campus.test', password_hash=password_hash, role='admin'))
        for index in range(45):
            db.add(User(username=f'demo_{index:03}', full_name='Демо Клиент', email=f'demo{index}@campus.test', password_hash=password_hash, is_demo=True))
    with login_staff(app) as staff:
        first = staff.get('/api/v1/staff/overview').json()
        assert first['clients'] == 47
        assert first['registered_clients'] == 2
        assert first['demo_clients'] == 45
        assert first['registered_today'] == first['blocked'] == 1
        assert signup(client, username='one_more_client').status_code == 201
        updated = staff.get('/api/v1/staff/overview').json()
        assert updated['clients'] == 48
        assert updated['registered_clients'] == 3
        assert updated['demo_clients'] == 45
        assert updated['registered_today'] == 2
