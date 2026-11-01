from pathlib import Path
import logging
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.exc import IntegrityError
from .config import settings
from .middleware.geo_access import GeoAccessMiddleware
from .api import auth, accounts, cards, dashboard, transfers, payments, transactions, profile, support, notifications, staff, catalog, legal, ai
from .services.consent import cookie_receipt

cfg = settings()
app = FastAPI(title="B bank API", version="1.0.0", docs_url="/api/docs" if cfg.app_env != "production" else None, redoc_url=None, openapi_url="/api/openapi.json" if cfg.app_env != "production" else None)

for module in [auth, accounts, cards, dashboard, transfers, payments, transactions, profile, support, notifications, staff, catalog, legal, ai]:
    app.include_router(module.router, prefix="/api/v1")

app.add_middleware(GeoAccessMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[s.strip() for s in cfg.allowed_hosts.split(",") if s.strip()])


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = str(uuid4())
    exempt = {"/api/v1/auth/me", "/api/v1/auth/options", "/api/v1/auth/logout", "/api/v1/public/content"}
    needs_terms = request.url.path.startswith("/api/v1/") and not request.url.path.startswith("/api/v1/legal/") and request.url.path not in exempt and not cookie_receipt(request)
    if request.url.path.startswith("/api/") and request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        allowed = {str(request.base_url).rstrip("/"), cfg.public_base_url.rstrip("/")}
        if origin and origin.rstrip("/") not in allowed:
            return JSONResponse({"detail": "Источник запроса не разрешён"}, status_code=403)
    try:
        response = JSONResponse({"detail": "Сначала ознакомьтесь с соглашениями и подтвердите условия"}, status_code=428) if needs_terms else await call_next(request)
    except Exception:
        logging.exception("Unhandled error, request_id=%s", request_id)
        response = JSONResponse({"detail": "Не удалось выполнить запрос. Попробуйте снова.", "request_id": request_id}, status_code=500)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    fields = [str(e['loc'][-1]) for e in exc.errors()]
    return JSONResponse({"detail": "Проверьте заполнение полей: " + ", ".join(dict.fromkeys(fields)), "fields": fields}, status_code=422)


@app.exception_handler(IntegrityError)
async def conflict(request, exc):
    return JSONResponse({"detail": "Данные уже изменились или операция повторилась. Обновите страницу."}, status_code=409)


@app.get("/api/health", include_in_schema=False)
def health():
    return {"status": "ok", "service": "campus-bank"}


dist = Path(cfg.frontend_dist).resolve()
if (dist / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
if (dist / "images").is_dir():
    app.mount("/images", StaticFiles(directory=dist / "images"), name="images")
if (dist / "brand-assets").is_dir():
    app.mount("/brand-assets", StaticFiles(directory=dist / "brand-assets"), name="brand-assets")


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    if path == "api" or path.startswith("api/"):
        raise HTTPException(404, "API-маршрут не найден")
    # Only explicit public assets can be served; arbitrary filesystem paths are never exposed.
    if path in ("favicon.svg", "logo.svg") and (dist / path).is_file():
        return FileResponse(dist / path)
    if not (dist / "index.html").is_file():
        return JSONResponse({"detail": "Интерфейс не собран. Выполните npm run build в frontend."}, status_code=503)
    return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})
