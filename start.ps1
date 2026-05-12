$ErrorActionPreference = "Stop"

Write-Host "🚗 KFZ Kontakt Setup" -ForegroundColor Cyan

# Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python nicht gefunden. Bitte Python installieren." -ForegroundColor Red
    exit 1
}

# Install dependencies
Write-Host "`n📦 Installiere Dependencies..." -ForegroundColor Yellow
Set-Location backend
pip install -r requirements.txt

# Create .env if not exists
if (-not (Test-Path ".env")) {
    Write-Host "`n📝 Erstelle .env Datei..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "⚠️  Bitte .env Datei mit deinen Telegram-Daten konfigurieren!" -ForegroundColor Yellow
}

# Start server
Write-Host "`n✅ Starte Server..." -ForegroundColor Green
python main.py
