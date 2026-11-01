"""Integration tests use the same disposable database fixture; no paid AI calls."""
import json
from datetime import timedelta
from uuid import uuid4
import pytest
import httpx
from pydantic import SecretStr
from test_registration_orders import bank, signup, headers, accept_terms


def message(client, body='Как оформить карту?', key=None, handoff=False):
    return client.post('/api/v1/ai/' + ('handoff' if handoff else 'chat'), json={"message": body, "request_key": key or str(uuid4())}, headers=headers(client))


def enable_ai(client):
    response = client.post('/api/v1/legal/ai-consent', json={"enabled": True}, headers=headers(client))
    assert response.status_code == 200, response.text


@pytest.fixture()
def fake_provider(monkeypatch):
    from app.config import settings
    cfg = settings()
    monkeypatch.setattr(cfg, 'ai_enabled', True)
    monkeypatch.setattr(cfg, 'ai_api_key', SecretStr('test-server-key-never-real'))
    monkeypatch.setattr(cfg, 'ai_model', 'test-json-model')
    monkeypatch.setattr(cfg, 'ai_api_format', 'openai_chat')
    calls = []
    result = {'reply': 'Выберите карту в каталоге и отправьте заявку.', 'escalate': False, 'reason': 'none'}
    real_client = httpx.Client
    def handler(request):
        calls.append((request, json.loads(request.content)))
        assert request.headers['authorization'] == 'Bearer test-server-key-never-real'
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(result, ensure_ascii=False)}}]})
    monkeypatch.setattr('app.services.ai_providers.httpx.Client', lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    return calls, result


def test_gate_requires_current_complete_explicit_acceptance(bank):
    client, _ = bank
    client.cookies.clear()
    assert signup(client).status_code == 428
    bundle = client.get('/api/v1/legal/status').json()
    assert bundle['accepted'] is False and len(bundle['documents']) == 4
    data = {"version": bundle['version'], "reviewed_documents": [d['id'] for d in bundle['documents']], "agree": True}
    assert client.post('/api/v1/legal/accept', json={**data, 'agree': False}).status_code == 400
    assert client.post('/api/v1/legal/accept', json={**data, 'reviewed_documents': ['website']}).status_code == 400
    assert client.post('/api/v1/legal/accept', json={**data, 'version': 'outdated'}).status_code == 409
    response = client.post('/api/v1/legal/accept', json=data)
    assert response.status_code == 200
    assert 'HttpOnly' in response.headers['set-cookie']
    assert client.get('/api/v1/legal/status').json()['accepted'] is True
    assert signup(client).status_code == 201
    from sqlalchemy import select
    from app.db import SessionLocal
    from app.models import ConsentReceipt, ConsentAcceptance
    with SessionLocal() as db:
        assert db.scalar(select(ConsentAcceptance.id)) is not None
        assert db.scalars(select(ConsentReceipt).where(ConsentReceipt.version == bundle['version'])).all()


def test_forged_cookie_and_changed_documents_require_new_acceptance(bank, monkeypatch):
    from app.config import settings
    client, _ = bank
    original = client.cookies.get('campus_terms')
    client.cookies.clear()
    client.cookies.set('campus_terms', original[:-1] + ('0' if original[-1] != '0' else '1'))
    assert message(client).status_code == 428
    client.cookies.clear()
    accept_terms(client)
    monkeypatch.setattr(settings(), 'organizer_name', 'Другой организатор')
    assert client.get('/api/v1/legal/status').json()['accepted'] is False
    assert signup(client).status_code == 428


def test_ai_requires_separate_consent_and_hides_numbers(bank, fake_provider):
    client, _ = bank
    calls, _ = fake_provider
    state = client.get('/api/v1/ai/state').json()
    assert state['conversation'] is None and state['ai_consent'] is False
    assert message(client).status_code == 403
    assert not calls
    enable_ai(client)
    response = message(client)
    assert response.status_code == 200, response.text
    assert len(calls) == 1
    assert response.json()['contacts'] == [] and response.json()['escalated'] is False
    assert 'test-server-key' not in response.text


def test_ai_http_payload_redaction_and_idempotency(bank, fake_provider):
    client, _ = bank
    calls, _ = fake_provider
    assert signup(client).status_code == 201
    enable_ai(client)
    body = 'Как оформить карту? пароль: secret12345 телефон +996220715205 ключ YOUR_SECRET_HERE и AQ.example_auth_key_abcdefghijklmnopqrstuvwxyz'
    key = str(uuid4())
    first = message(client, body, key)
    assert first.status_code == 200, first.text
    second = message(client, body, key)
    assert second.status_code == 200 and len(calls) == 1
    assert len(second.json()['messages']) == 2
    assert message(client, 'Другой вопрос', key).status_code == 409 and len(calls) == 1
    sent = json.dumps(calls[0][1], ensure_ascii=False)
    for secret in ['secret12345', '996220715205', 'YOUR_SECRET_HERE', 'AQ.example_auth_key_abcdefghijklmnopqrstuvwxyz', 'example_user@campus.test']:
        assert secret not in sent and secret not in first.text
    assert calls[0][1]['model'] == 'test-json-model'
    assert calls[0][1]['response_format']['type'] == 'json_object'
    assert calls[0][0].url.path.endswith('/chat/completions')


def test_model_escalation_reveals_contacts_and_creates_one_ticket(bank, fake_provider):
    client, _ = bank
    calls, result = fake_provider
    assert signup(client).status_code == 201
    enable_ai(client)
    result.update(reply='Нужна проверка организатором.', escalate=True, reason='complex')
    key = str(uuid4())
    response = message(client, 'Проверьте конкретную учебную операцию.', key)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['escalated'] is True and data['ticket_id']
    assert [c['number'] for c in data['contacts']] == ['996220715205', '996995393911']
    assert len(client.get('/api/v1/support/tickets').json()) == 1
    assert message(client, 'Проверьте конкретную учебную операцию.', key).status_code == 200
    assert len(calls) == 1 and len(client.get('/api/v1/support/tickets').json()) == 1


@pytest.mark.parametrize('body,handoff', [('Хочу связаться с оператором', False), ('Мой аккаунт взломали', False), ('Помощь человека', True)])
def test_urgent_or_human_request_needs_no_external_ai_consent(bank, fake_provider, body, handoff):
    client, _ = bank
    calls, _ = fake_provider
    response = message(client, body, handoff=handoff)
    assert response.status_code == 200, response.text
    assert response.json()['escalated'] is True
    assert response.json()['contacts'] and response.json()['ticket_id'] is None
    assert not calls


def test_provider_failure_or_invalid_json_hands_off(bank, fake_provider):
    client, _ = bank
    _, result = fake_provider
    enable_ai(client)
    result.update(escalate='false')  # StrictBool rejects a provider's malformed output.
    response = message(client)
    assert response.status_code == 200, response.text
    assert response.json()['escalated'] is True and response.json()['contacts']
    assert 'недоступен' in response.json()['reason']


def test_guest_and_account_histories_are_isolated_and_withdrawal_deletes_chats(bank, fake_provider):
    from fastapi.testclient import TestClient
    client, app = bank
    enable_ai(client)
    assert message(client).status_code == 200
    with TestClient(app) as other:
        accept_terms(other)
        assert other.get('/api/v1/ai/state').json()['conversation'] is None
    assert signup(client).status_code == 201
    assert client.get('/api/v1/ai/state').json()['conversation'] is None
    assert message(client).status_code == 200
    assert client.post('/api/v1/legal/ai-consent', json={'enabled': False}).status_code == 403
    assert client.post('/api/v1/legal/ai-consent', json={'enabled': False}, headers=headers(client)).status_code == 200
    state = client.get('/api/v1/ai/state').json()
    assert state['ai_consent'] is False and state['conversation'] is None
    assert message(client).status_code == 403


def test_hourly_budget_prevents_extra_provider_calls(bank, fake_provider, monkeypatch):
    from app.config import settings
    client, _ = bank
    calls, _ = fake_provider
    monkeypatch.setattr(settings(), 'ai_hourly_limit', 1)
    enable_ai(client)
    assert message(client).status_code == 200
    assert message(client, 'А как получить выписку?').status_code == 429
    assert len(calls) == 1
    assert message(client, handoff=True).status_code == 200


def test_stale_pending_answer_recovers_as_handoff(bank, fake_provider):
    from sqlalchemy import select
    from app.db import SessionLocal
    from app.models import AiConversation
    from app.models.identity import now
    client, _ = bank
    enable_ai(client)
    assert message(client).status_code == 200
    with SessionLocal.begin() as db:
        conversation = db.scalar(select(AiConversation))
        conversation.pending_key, conversation.pending_at = str(uuid4()), now()-timedelta(minutes=1)
    state = client.get('/api/v1/ai/state')
    assert state.status_code == 200, state.text
    assert state.json()['conversation']['pending'] is False
    assert state.json()['conversation']['escalated'] is True


@pytest.mark.parametrize('api_format,base,model', [
    ('openai_chat','https://gateway.example.test/api/v1','some-company/some-text-model'),
    ('openai_responses','https://api.openai.com/v1','some-reasoning-model'),
    ('anthropic','https://api.anthropic.com/v1','some-claude-model'),
    ('gemini','https://generativelanguage.googleapis.com/v1beta','some-gemini-model'),
])
def test_provider_adapters_use_arbitrary_model_ids_and_correct_protocol(bank, monkeypatch, api_format, base, model):
    from app.config import settings
    cfg = settings()
    for name,value in {'ai_enabled':True,'ai_api_key':SecretStr('provider-test-only'),'ai_api_format':api_format,'ai_api_base_url':base,'ai_model':model}.items():
        monkeypatch.setattr(cfg, name, value)
    raw=json.dumps({'reply':'Откройте каталог продуктов.','escalate':False,'reason':'none'},ensure_ascii=False)
    seen=[]
    def handler(request):
        payload=json.loads(request.content)
        seen.append(payload)
        assert 'provider-test-only' not in str(request.url)
        if api_format=='anthropic':
            assert request.headers['x-api-key']=='provider-test-only'
            assert request.headers['anthropic-version']=='2023-06-01'
            assert request.url.path.endswith('/messages') and payload['system']
            assert payload['model']==model and payload['max_tokens']==600
            return httpx.Response(200,json={'content':[{'type':'text','text':raw}]})
        if api_format=='gemini':
            assert request.headers['x-goog-api-key']=='provider-test-only'
            assert request.url.path.endswith('/models/'+model+':generateContent')
            assert payload['systemInstruction'] and payload['contents'][0]['role']=='user'
            assert payload['generationConfig']['responseMimeType']=='application/json'
            return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':raw}]}}]})
        assert request.headers['authorization']=='Bearer provider-test-only'
        assert payload['model']==model
        if api_format=='openai_responses':
            assert request.url.path.endswith('/responses') and payload['store'] is False
            assert payload['instructions'] and payload['text']['format']['type']=='json_object'
            return httpx.Response(200,json={'output':[{'type':'message','content':[{'type':'output_text','text':raw}]}]})
        assert request.url.path.endswith('/chat/completions')
        return httpx.Response(200,json={'choices':[{'message':{'content':raw}}]})
    real_client=httpx.Client
    monkeypatch.setattr('app.services.ai_providers.httpx.Client',lambda **kwargs:real_client(transport=httpx.MockTransport(handler),**kwargs))
    client,_=bank
    enable_ai(client)
    response=message(client)
    assert response.status_code==200,response.text
    assert response.json()['escalated'] is False and len(seen)==1
    assert 'Откройте каталог' in response.json()['messages'][-1]['body']


def test_b_bank_branding_and_downloadable_assets(bank):
    client, _ = bank
    content = client.get('/api/v1/public/content').json()
    assert content['products'][0]['name'] == 'B Black'
    assert client.get('/api/v1/auth/options').json()['bank_name'] == 'B bank'
    bundle = client.get('/api/v1/legal/status').json()
    assert all('Campus' not in doc['title'] for doc in bundle['documents'])
    for asset in ['b-symbol.svg','b-bank-logo.svg','b-round.svg','b-bank-inverse.svg','b-bank-presentation.svg','logo-primary.png','logo-round.png','logo-inverse.png','presentation-cover.png']:
        response=client.get('/brand-assets/'+asset)
        assert response.status_code==200,(asset,response.text[:100])
        assert response.headers['content-type'].startswith('image/')
