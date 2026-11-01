"""Check configured AI with a synthetic question, without printing credentials."""
import sys
import httpx
from bootstrap import ROOT
from app.config import settings
from app.services.ai_providers import complete

def main():
    try:
        cfg=settings()
    except Exception:
        print('Ошибка настроек. Проверьте .env, DATABASE_URL, APP_SECRET и AI_API_BASE_URL. Значения секретов скрыты.')
        return 1
    if not cfg.ai_enabled:
        print('AI выключен: установите AI_ENABLED=true в .env и перезапустите сервер.')
        return 1
    try:
        reply=complete(cfg,'Ответь JSON-объектом {"answer":"Подключение работает"}.', [{'role':'user','body':'Проверка подключения учебного сайта. Реальных данных нет.'}])
        if not reply.strip():
            print('Провайдер вернул пустой ответ. Проверьте модель и лимит токенов.')
            return 1
        print('УСПЕХ: провайдер вернул непустой ответ на тестовый вопрос. Ключ не выводится.')
        return 0
    except httpx.HTTPStatusError as exc:
        status=exc.response.status_code
        hint={400:'Неверный формат запроса, ключ или параметры модели.',401:'Ключ отклонён.',403:'Нет доступа: проверьте права ключа, проект и доступность сервиса.',404:'Модель или адрес API не найдены.',429:'Исчерпана квота или превышен лимит запросов.'}.get(status,'Ошибка на стороне API; проверьте журнал провайдера.')
        print(f'HTTP {status}: {hint}')
    except httpx.TimeoutException:
        print('Превышено время ожидания ответа API.')
    except httpx.HTTPError:
        print('Нет сетевого соединения с API. Ключ не проверен: проверьте DNS, сеть и доступность провайдера.')
    except (ValueError,KeyError,IndexError,TypeError):
        print('Ответ API имеет неподдерживаемый формат. Проверьте AI_API_FORMAT и AI_MODEL.')
    return 2
if __name__=='__main__':
    sys.exit(main())
