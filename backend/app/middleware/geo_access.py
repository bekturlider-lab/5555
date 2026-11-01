from pathlib import Path
import maxminddb
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse, JSONResponse
from ..config import settings
from ..core.trusted_proxy import client_ip


class GeoAccessMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.reader = None
        cfg = settings()
        if cfg.geoblock_enabled and Path(cfg.geoip_db_path).is_file():
            self.reader = maxminddb.open_database(cfg.geoip_db_path)

    async def dispatch(self, request, call_next):
        cfg = settings()
        if cfg.geoblock_enabled and request.url.path != "/api/health":
            ip = client_ip(request, cfg.trusted_proxy_cidrs)
            country = None
            try:
                record = self.reader.get(ip) if self.reader and ip else None
                country = (record or {}).get("country", {}).get("iso_code")
            except (ValueError, maxminddb.errors.InvalidDatabaseError):
                pass
            denied = {c.strip().upper() for c in cfg.geoblock_deny_countries.split(",")}
            if not country or country in denied:
                if request.url.path.startswith("/api/"):
                    return JSONResponse({"detail": "Доступ из этой сети ограничен", "code": "geo_blocked"}, status_code=403)
                template = Path(__file__).resolve().parents[1] / "templates" / "access_denied.html"
                return HTMLResponse(template.read_text(), status_code=403)
        return await call_next(request)
