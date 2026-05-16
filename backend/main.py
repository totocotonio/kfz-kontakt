# -*- coding: utf-8 -*-
# © 2026 Torsten Michaely - KFZ Kontakt QR-Code System
# Mit WhatsApp-Integration für flexible Kontaktmöglichkeiten
# All rights reserved

from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
from models import Base, Category, QRCode
from database import engine, get_db, SessionLocal
from routes import scanner, qrcode, dashboard
from config import settings
from auth import verify_dashboard_auth
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
import os
import io
import re
from html import escape
import json

limiter = Limiter(key_func=get_remote_address)

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db = SessionLocal()
    try:
        from models import User, Category
        existing_user = db.query(User).first()
        if not existing_user:
            user = User(name="Admin", telegram_chat_id="0")
            db.add(user)
            db.commit()

        categories = [
            ("Parkplatz", "Falsches Parken oder Parkschaden", "🅿️"),
            ("Beleuchtung", "Licht vergessen oder defekt", "💡"),
            ("Fenster", "Fenster offen", "🪟"),
            ("Schaden", "Fahrzeug beschädigt", "⚠️"),
            ("Sonstiges", "Andere Mitteilung", "📝"),
        ]

        for name, desc, icon in categories:
            existing_cat = db.query(Category).filter(Category.name == name).first()
            if not existing_cat:
                cat = Category(name=name, description=desc, icon=icon)
                db.add(cat)
        db.commit()
    finally:
        db.close()

    yield
    # Shutdown (optional cleanup)

app = FastAPI(title="KFZ Kontakt QR", version="1.0.32", lifespan=lifespan)

# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(Exception, lambda request, exc: {"error": "Rate limit exceeded"})

# Parse allowed origins from settings
allowed_origins = [settings.BASE_URL]
if "," in settings.ALLOWED_ORIGINS:
    allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]
else:
    allowed_origins = [settings.ALLOWED_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

# Security Headers Middleware - CRITICAL for security
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # Legacy XSS protection
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # HSTS - enforce HTTPS
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    # Content Security Policy - prevent inline scripts
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
    return response

app.include_router(scanner.router)
app.include_router(qrcode.router)
app.include_router(dashboard.router)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

def get_dashboard_version():
    """Read version from file"""
    try:
        version_file = Path(__file__).parent.parent / "version.txt"
        with open(version_file, "r") as f:
            return f.read().strip()
    except:
        return "unknown"

@app.api_route("/dashboard/", methods=["GET", "HEAD"])
def dashboard_index():
    """Serve dashboard HTML with injected version - MUST be before StaticFiles mount"""
    # KEIN Auth-Check hier! Auth passiert nur bei API-Calls im JavaScript

    frontend_dir = Path(__file__).parent.parent / "frontend"
    index_file = frontend_dir / "dashboard" / "index.html"

    if not index_file.exists():
        return {"error": "Dashboard nicht gefunden"}

    # Get current version
    version = get_dashboard_version()

    # Read HTML
    with open(index_file, "r", encoding="utf-8") as f:
        html = f.read()

    # Inject version into HTML - CRITICAL for version display
    html = html.replace('<span id="version">-</span>', f'<span id="version">{version}</span>')
    html = html.replace('<!--VERSION-->', version)  # Fallback injection point

    # CRITICAL: Inject version into script src to prevent JS caching
    # Changes script src from "js/dashboard.js?v=0" to "js/dashboard.js?v=1.0.55" to force browser to re-fetch
    html = re.sub(r'js/dashboard\.js\?v=[\d.]+', f'js/dashboard.js?v={version}', html)

    # Return with AGGRESSIVE no-cache headers
    from starlette.responses import HTMLResponse
    import time
    response = HTMLResponse(html)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Version"] = version  # Debug header
    response.headers["X-Timestamp"] = str(int(time.time()))  # Force cache invalidation with timestamp
    return response

# Mount static files AFTER the /dashboard/ endpoint to avoid conflicts
if FRONTEND_DIR.exists():
    # Mount js and css directories separately
    for subdir in ["js", "css"]:
        subdir_path = FRONTEND_DIR / "dashboard" / subdir
        if subdir_path.exists():
            app.mount(f"/dashboard/{subdir}", StaticFiles(directory=subdir_path), name=f"dashboard_{subdir}")

# Mount uploads directory for vehicle images
UPLOADS_DIR = Path(settings.UPLOAD_DIR)
if not UPLOADS_DIR.exists():
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

@app.get("/favicon.ico")
def favicon():
    """Serve favicon"""
    favicon_path = FRONTEND_DIR / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    return {"error": "favicon not found"}

@app.get("/favicon.png")
def favicon_png():
    """Serve favicon PNG"""
    favicon_path = FRONTEND_DIR / "favicon.png"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    return {"error": "favicon not found"}

@app.get("/manifest.json")
def manifest():
    """Serve manifest.json for PWA"""
    manifest_path = FRONTEND_DIR / "manifest.json"
    if manifest_path.exists():
        return FileResponse(manifest_path, media_type="application/manifest+json")
    return {"error": "manifest.json not found"}

@app.get("/select-category.html")
def select_category_page(qr: str = None):
    """Serve category selection page"""
    if not qr:
        return {"error": "QR code not provided"}

    category_path = FRONTEND_DIR / "qr" / "select-category.html"
    if not category_path.exists():
        return {"error": "select-category.html not found"}

    with open(category_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Inject QR ID (escaped to prevent XSS)
    html = html.replace(
        "const uniqueId = '';",
        f"const uniqueId = {json.dumps(qr)};"
    )

    return HTMLResponse(content=html)

@app.get("/qr/{unique_id}")
def qr_page(unique_id: str, category: int = None, db: Session = Depends(get_db)):
    """Serve QR page - either landing page or contact form"""
    # Verify QR code exists
    qr = db.query(QRCode).filter(QRCode.unique_id == unique_id).first()
    if not qr:
        return {"error": "QR code not found"}, 404

    # If category is selected, show contact form
    if category is not None:
        contact_form_path = FRONTEND_DIR / "qr" / "contact-form.html"
        if not contact_form_path.exists():
            return {"error": "contact-form.html not found"}

        with open(contact_form_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Inject data (escaped to prevent XSS)
        html = html.replace(
            "const uniqueId = '';",
            f"const uniqueId = {json.dumps(unique_id)};"
        )
        html = html.replace(
            "const selectedCategory = '';",
            f"const selectedCategory = {json.dumps(str(category)) if category else 'null'};"
        )

        return HTMLResponse(content=html)

    # Otherwise show vehicle landing page
    landing_path = FRONTEND_DIR / "qr" / "vehicle-landing.html"
    if not landing_path.exists():
        return {"error": "vehicle-landing.html not found"}

    with open(landing_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Inject data into JavaScript (escaped to prevent XSS)
    html = html.replace(
        "const uniqueId = '';",
        f"const uniqueId = {json.dumps(unique_id)};"
    )
    html = html.replace(
        "const licensePlate = '';",
        f"const licensePlate = {json.dumps(qr.license_plate or '')};"
    )
    html = html.replace(
        "const vehicleImagePath = '';",
        f"const vehicleImagePath = {json.dumps(qr.vehicle_image_path or '')};"
    )

    return HTMLResponse(content=html)

@app.get("/")
def read_root():
    return {"message": "KFZ Kontakt QR API läuft"}

@app.get("/debug/auth")
def debug_auth(request: Request):
    verify_dashboard_auth(request)
    return {
        "dashboard_password_set": bool(settings.DASHBOARD_PASSWORD),
        "message": "Debug info nur für authentifizierte Admins verfügbar"
    }

@app.get("/debug/reload")
def debug_reload(request: Request):
    """Reload database and models - für Development/Testing"""
    verify_dashboard_auth(request)
    try:
        from models import Base
        from database import engine
        import importlib
        import sys

        # Reload models
        if 'models' in sys.modules:
            importlib.reload(sys.modules['models'])

        # Recreate tables if missing
        Base.metadata.create_all(bind=engine)

        return {
            "status": "success",
            "message": "Models und Datenbank neu geladen",
            "version": get_dashboard_version()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/api/version")
def get_version():
    try:
        import os
        version_file = os.path.join(os.path.dirname(__file__), "..", "version.txt")
        with open(version_file, "r") as f:
            version = f.read().strip()
    except:
        version = "unknown"
    # No-cache Headers um Browser-Cache zu verhindern
    return {
        "version": version,
        "cached": False  # Keine Cache-Nutzung
    }

@app.get("/api/categories")
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    return {
        "categories": [
            {
                "id": cat.id,
                "name": cat.name,
                "icon": cat.icon
            }
            for cat in categories
        ]
    }

@app.get("/datenschutz.html")
def datenschutz_page():
    """Serve datenschutz.html - Datenschutzerklärung"""
    frontend_dir = Path(__file__).parent.parent / "frontend"
    datenschutz_file = frontend_dir / "datenschutz.html"
    if datenschutz_file.exists():
        return FileResponse(datenschutz_file, media_type="text/html")
    return {"error": "Datenschutzerklärung nicht gefunden"}

@app.get("/datenschutz")
def datenschutz_redirect():
    """Redirect /datenschutz to /datenschutz.html"""
    return RedirectResponse(url="/datenschutz.html", status_code=302)

@app.get("/impressum.html")
def impressum_page():
    """Serve impressum.html - Impressum"""
    frontend_dir = Path(__file__).parent.parent / "frontend"
    impressum_file = frontend_dir / "impressum.html"
    if impressum_file.exists():
        return FileResponse(impressum_file, media_type="text/html")
    return {"error": "Impressum nicht gefunden"}

@app.get("/impressum")
def impressum_redirect():
    """Redirect /impressum to /impressum.html"""
    return RedirectResponse(url="/impressum.html", status_code=302)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
