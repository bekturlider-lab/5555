"""Text-generation adapters. Model IDs are operator settings, not a fixed list."""
from urllib.parse import quote
import httpx


def complete(cfg, system, history):
    base = cfg.ai_api_base_url.rstrip('/')
    key = cfg.ai_api_key.get_secret_value()
    messages = [{"role": m['role'], "content": m['body']} for m in history[-10:]]
    # Truncated history may begin with an assistant turn; retain a user-first chat.
    while messages and messages[0]['role'] != 'user':
        messages.pop(0)
    headers = {"Content-Type": "application/json"}
    if cfg.ai_api_format == 'anthropic':
        url = base + '/messages'
        headers.update({"x-api-key": key, "anthropic-version": "2023-06-01"})
        payload = {"model": cfg.ai_model, "system": system, "messages": messages, "max_tokens": cfg.ai_max_output_tokens, "stream": False}
    elif cfg.ai_api_format == 'gemini':
        model = quote(cfg.ai_model.removeprefix('models/'), safe='-_.')
        url = base + '/models/' + model + ':generateContent'
        headers['x-goog-api-key'] = key
        generation = {"maxOutputTokens": cfg.ai_max_output_tokens}
        if cfg.ai_json_mode:
            generation['responseMimeType'] = 'application/json'
        payload = {"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"role": 'model' if m['role'] == 'assistant' else 'user', "parts": [{"text": m['content']}]} for m in messages], "generationConfig": generation}
    elif cfg.ai_api_format == 'openai_responses':
        url = base + '/responses'
        headers['Authorization'] = 'Bearer ' + key
        payload = {"model": cfg.ai_model, "instructions": system, "input": messages, "max_output_tokens": cfg.ai_max_output_tokens, "store": False, "stream": False}
        if cfg.ai_json_mode:
            payload['text'] = {"format": {"type": "json_object"}}
    else:
        url = base + '/chat/completions'
        headers['Authorization'] = 'Bearer ' + key
        payload = {"model": cfg.ai_model, "messages": [{"role": "system", "content": system}] + messages, cfg.ai_token_parameter: cfg.ai_max_output_tokens, "stream": False}
        if cfg.ai_json_mode:
            payload['response_format'] = {"type": "json_object"}
    with httpx.Client(timeout=cfg.ai_timeout_seconds, follow_redirects=False, trust_env=False) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        if len(response.content) > 65536:
            raise ValueError('Oversized provider response')
        body = response.json()
    if cfg.ai_api_format == 'anthropic':
        return ''.join(item['text'] for item in body['content'] if item.get('type') == 'text')
    if cfg.ai_api_format == 'gemini':
        return ''.join(item.get('text', '') for item in body['candidates'][0]['content']['parts'] if not item.get('thought'))
    if cfg.ai_api_format == 'openai_responses':
        return ''.join(item['text'] for output in body['output'] if output.get('type') == 'message' for item in output.get('content', []) if item.get('type') == 'output_text')
    return body['choices'][0]['message']['content']
