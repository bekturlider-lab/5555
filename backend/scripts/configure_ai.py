"""Local secret setup; credentials are read without terminal echo, never as CLI args."""
import argparse
import getpass
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Настройка серверного AI-ключа B bank')
    parser.add_argument('--provider', choices=['gemini','anthropic','openai_chat','openai_responses'], default='gemini')
    parser.add_argument('--model', default='gemini-2.5-flash-lite')
    parser.add_argument('--base-url', default='')
    parser.add_argument('--label', default='')
    args = parser.parse_args()
    key = getpass.getpass('API-ключ (ввод скрыт): ').strip()
    if not key or any(c in key for c in '\r\n'):
        parser.error('Пустой или некорректный ключ')
    path = ROOT / '.env'
    content = path.read_text() if path.exists() else (ROOT / '.env.example').read_text()
    updates = {'AI_ENABLED':'true','AI_API_FORMAT':args.provider,'AI_API_BASE_URL':args.base_url,'AI_PROVIDER_LABEL':args.label,'AI_MODEL':args.model,'AI_API_KEY':key}
    for name,value in updates.items():
        line = name + '=' + value
        if re.search('^'+name+'=',content,re.M):
            content = re.sub('^'+name+'=.*$',lambda _:line,content,flags=re.M)
        else:
            content = content.rstrip()+'\n'+line+'\n'
    descriptor = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(descriptor,'w') as handle:
        handle.write(content)
    path.chmod(0o600)
    print('Серверный ключ сохранён в .env. Перезапустите приложение. В архив и Git этот файл не включайте.')
