#!/bin/bash
set -e

echo "🚗 KFZ Kontakt Deployment auf Debian LXC"

# Update system
echo "📦 Update system..."
apt update && apt upgrade -y

# Install Python & dependencies
echo "🐍 Install Python & pip..."
apt install -y python3 python3-pip python3-venv git

# Create app directory
echo "📁 Create app directory..."
mkdir -p /opt/kfz-kontakt
cd /opt/kfz-kontakt

# Clone or copy repo (adjust git URL if needed)
# If you already have the files, skip this
# git clone https://github.com/yourusername/kfz-kontakt.git .

# Create virtual environment
echo "🔧 Create virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "📥 Install Python packages..."
cd backend
pip install -r requirements.txt

# Create .env file
echo "📝 Create .env file..."
cat > .env << 'EOF'
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
TELEGRAM_CHAT_ID=YOUR_CHAT_ID_HERE
DATABASE_URL=sqlite:///./kfz_kontakt.db
DEBUG=False
HOST=0.0.0.0
PORT=8000
EOF

echo ""
echo "⚠️  WICHTIG: .env Datei konfigurieren!"
echo "nano /opt/kfz-kontakt/backend/.env"
echo ""
echo "Setze:"
echo "- TELEGRAM_BOT_TOKEN: Dein Telegram Bot Token"
echo "- TELEGRAM_CHAT_ID: Deine Telegram Chat ID"
echo ""
echo "Nach der Konfiguration:"
echo "source /opt/kfz-kontakt/venv/bin/activate"
echo "cd /opt/kfz-kontakt/backend"
echo "python3 main.py"
echo ""
echo "✅ Deployment fertig!"
