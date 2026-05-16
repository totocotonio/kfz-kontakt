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

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
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
        return FileResponse("404.html", status_code=404)

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
def debug_auth(password: str = Depends(verify_dashboard_auth)):
    return {
        "dashboard_password_set": bool(settings.DASHBOARD_PASSWORD),
        "message": "Debug info nur für authentifizierte Admins verfügbar"
    }

@app.get("/debug/reload")
def debug_reload(password: str = Depends(verify_dashboard_auth)):
    """Reload database and models - für Development/Testing"""
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

@app.get("/select-category.html")
def select_category_page():
    frontend_dir = Path(__file__).parent.parent / "frontend"
    select_cat_file = frontend_dir / "qr" / "select-category.html"
    if select_cat_file.exists():
        return FileResponse(select_cat_file, media_type="text/html")
    return {"error": "File not found"}

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

@app.get("/qr/vehicle-landing.html")
def vehicle_landing_page(qr: str = None, license_plate: str = None, vehicle_image_path: str = None):
    frontend_dir = Path(__file__).parent.parent / "frontend"
    vehicle_landing_file = frontend_dir / "qr" / "vehicle-landing.html"
    if vehicle_landing_file.exists():
        with open(vehicle_landing_file, 'r', encoding='utf-8') as f:
            html = f.read()

        # Injiziere die Parameter direkt ins JavaScript (mit URL-Encoding für Sonderzeichen)
        html = html.replace("const uniqueId = '';", f"const uniqueId = '{qr or ''}';")
        html = html.replace("const licensePlate = '';", f"const licensePlate = '{license_plate or ''}';")
        html = html.replace("const vehicleImagePath = '';", f"const vehicleImagePath = '{vehicle_image_path or ''}';")

        return HTMLResponse(html)
    return {"error": "File not found"}

@app.get("/qr/{unique_id}")
def scanner_page(unique_id: str, category: int = None, db: Session = Depends(get_db)):
    # Wenn category nicht gesetzt, prüfe auf Fahrzeugbild
    if not category:
        qr = db.query(QRCode).filter(QRCode.unique_id == unique_id).first()

        # Wenn Fahrzeugbild vorhanden, zeige Vehicle Landing Page
        if qr and qr.vehicle_image_path:
            from urllib.parse import urlencode
            params = urlencode({
                "qr": unique_id,
                "license_plate": qr.license_plate or "",
                "vehicle_image_path": qr.vehicle_image_path
            })
            return RedirectResponse(url=f"/qr/vehicle-landing.html?{params}", status_code=302)

        # Fallback: Redirect zur Kategorie-Auswahl
        return RedirectResponse(url=f"/select-category.html?qr={unique_id}", status_code=302)

    # Kategorie ist gesetzt: Zeige externe Kontaktform mit injizierter Kategorie
    frontend_dir = Path(__file__).parent.parent / "frontend"
    contact_form_file = frontend_dir / "qr" / "contact-form.html"
    if contact_form_file.exists():
        with open(contact_form_file, 'r', encoding='utf-8') as f:
            html = f.read()

        # Injiziere die Parameter ins JavaScript
        html = html.replace("const uniqueId = '';", f"const uniqueId = '{unique_id}';")
        html = html.replace("const selectedCategory = '';", f"const selectedCategory = '{category}';")

        return HTMLResponse(html)

    return {"error": "Contact form not found"}

    scanner_html_old = """
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fahrzeug Kontakt</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
            .container { background: white; border-radius: 12px; padding: 30px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); max-width: 500px; width: 100%; }
            h1 { color: #333; margin-bottom: 10px; font-size: 24px; }
            .subtitle { color: #666; margin-bottom: 30px; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 8px; color: #333; font-weight: 500; }
            input, textarea, select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 16px; font-family: inherit; }
            textarea { resize: vertical; min-height: 100px; }
            input:focus, textarea:focus, select:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.1); }
            button { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: 600; cursor: pointer; transition: background 0.3s; }
            button:hover { background: #5568d3; }
            .error { color: #e74c3c; margin-top: 10px; }
            .success { color: #27ae60; margin-top: 10px; }
            .loading { display: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚗 Fahrzeug Kontakt</h1>
            <p class="subtitle">Hinterlasse eine Nachricht für den Fahrzeughalter</p>

            <form id="contactForm">
                <div class="form-group">
                    <label for="name">Dein Name (optional)</label>
                    <input type="text" id="name" name="name" placeholder="z.B. Max Mustermann">
                </div>

                <div class="form-group">
                    <label for="contact">Deine Kontakt (optional)</label>
                    <input type="text" id="contact" name="contact" placeholder="Tel oder WhatsApp: +49...">
                </div>

                <div class="form-group">
                    <label for="category">Kategorie (optional)</label>
                    <select id="category" name="category">
                        <option value="">-- Wähle eine Kategorie --</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="message">Deine Nachricht *</label>
                    <textarea id="message" name="message" placeholder="Beschreibe dein Anliegen..." required></textarea>
                </div>

                <div id="whatsappSection" style="margin-bottom: 20px;"></div>

                <button type="submit">Nachricht senden</button>
                <div class="loading" id="loading">Wird gesendet...</div>
                <div id="feedback"></div>
            </form>
        </div>

        <script>
            const uniqueId = """ + f'"{unique_id}"' + """;
            const selectedCategory = """ + f'"{category}"' + """;

            async function loadCategories() {
                try {
                    const res = await fetch(`/api/categories`);
                    const data = await res.json();
                    const select = document.getElementById('category');
                    data.categories.forEach(cat => {
                        const option = document.createElement('option');
                        option.value = cat.id;
                        option.textContent = cat.name;
                        select.appendChild(option);
                    });

                    // Vorauswahl wenn category parameter gesetzt
                    if (selectedCategory) {
                        select.value = selectedCategory;
                    }
                } catch(e) {
                    console.error('Fehler beim Laden der Kategorien:', e);
                }
            }

            async function loadWhatsAppButton() {
                try {
                    const res = await fetch(`/api/whatsapp`);
                    const data = await res.json();
                    const section = document.getElementById('whatsappSection');

                    if (data.whatsapp_number && data.whatsapp_number.trim()) {
                        const waNumber = data.whatsapp_number.replace(/[^0-9]/g, '');
                        if (waNumber) {
                            const waUrl = `https://wa.me/${waNumber}?text=Hallo, ich habe dir eine Nachricht über den QR-Code hinterlassen.`;
                            section.innerHTML = `
                                <a href="${waUrl}" target="_blank" style="display: block; padding: 12px; background: #25D366; color: white; text-align: center; border-radius: 6px; text-decoration: none; font-weight: 600; margin-bottom: 10px;">
                                    💬 Oder direkt WhatsApp schreiben
                                </a>
                            `;
                        }
                    }
                } catch(e) {
                    console.error('WhatsApp laden fehlgeschlagen:', e);
                }
            }

            document.getElementById('contactForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const feedback = document.getElementById('feedback');
                const loading = document.getElementById('loading');

                const payload = {
                    sender_name: document.getElementById('name').value || 'Anonym',
                    sender_contact: document.getElementById('contact').value,
                    category_id: document.getElementById('category').value ? parseInt(document.getElementById('category').value) : null,
                    message: document.getElementById('message').value
                };

                loading.style.display = 'block';
                feedback.innerHTML = '';

                try {
                    const res = await fetch(`/api/qr/${uniqueId}/message`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });

                    if (res.ok) {
                        const categorySelect = document.getElementById('category');
                        const categoryText = categorySelect.options[categorySelect.selectedIndex]?.text || '';
                        const message = payload.message;
                        const summary = `${categoryText ? categoryText + ' - ' : ''}${message}`;

                        feedback.innerHTML = '<p class="success">✅ Nachricht erfolgreich gesendet!</p>';

                        // Versuche WhatsApp Button zu laden
                        try {
                            const waRes = await fetch(`/api/whatsapp`);
                            const waData = await waRes.json();
                            if (waData.whatsapp_number && waData.whatsapp_number.trim()) {
                                const waNumber = waData.whatsapp_number.replace(/[^0-9]/g, '');
                                if (waNumber) {
                                    const waUrl = `https://wa.me/${waNumber}?text=${encodeURIComponent('Ich habe dir eine Nachricht über den QR-Code hinterlassen: ' + summary)}`;;
                                    feedback.innerHTML += `<a href="${waUrl}" target="_blank" style="display: block; padding: 12px; background: #25D366; color: white; text-align: center; border-radius: 6px; text-decoration: none; font-weight: 600; margin-top: 10px; margin-bottom: 10px;">💬 Oder direkt WhatsApp schreiben</a>`;
                                }
                            }
                        } catch(e) {
                            console.error('WhatsApp nach Nachricht:', e);
                        }

                        document.getElementById('contactForm').reset();
                    } else {
                        feedback.innerHTML = '<p class="error">❌ Fehler beim Senden der Nachricht</p>';
                    }
                } catch(e) {
                    feedback.innerHTML = '<p class="error">❌ Fehler: ' + e.message + '</p>';
                }
                loading.style.display = 'none';
            });

            loadCategories();
            loadWhatsAppButton();
        </script>
    </body>
    </html>
    """
    return StreamingResponse(
        io.BytesIO(scanner_html.encode()),
        media_type="text/html"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
