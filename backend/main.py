from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from models import Base
from database import engine, get_db, SessionLocal
from routes import scanner, qrcode, dashboard
from config import settings
import os
import io

Base.metadata.create_all(bind=engine)

app = FastAPI(title="KFZ Kontakt QR", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scanner.router)
app.include_router(qrcode.router)
app.include_router(dashboard.router)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "dashboard"), name="static")

@app.get("/")
def read_root():
    return {"message": "KFZ Kontakt QR API läuft"}

@app.on_event("startup")
def startup():
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

@app.get("/qr/{unique_id}")
def scanner_page(unique_id: str):
    scanner_html = """
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

                <button type="submit">Nachricht senden</button>
                <div class="loading" id="loading">Wird gesendet...</div>
                <div id="feedback"></div>
            </form>
        </div>

        <script>
            const uniqueId = """ + f'"{unique_id}"' + """;

            async function loadCategories() {
                try {
                    const res = await fetch(`/api/qr/${uniqueId}/info`);
                    const data = await res.json();
                    const select = document.getElementById('category');
                    data.categories.forEach(cat => {
                        const option = document.createElement('option');
                        option.value = cat.id;
                        option.textContent = cat.name;
                        select.appendChild(option);
                    });
                } catch(e) {
                    console.error('Fehler beim Laden der Kategorien:', e);
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
                        feedback.innerHTML = '<p class="success">✅ Nachricht erfolgreich gesendet!</p>';
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
        </script>
    </body>
    </html>
    """
    return FileResponse(io.BytesIO(scanner_html.encode()), media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
