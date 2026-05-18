#!/bin/bash
cd /opt/kfz-kontakt
git pull origin main
# Version aus version.txt auslesen
VERSION=$(cat version.txt)
echo "🚀 Deployment v$VERSION..."
systemctl restart kfz-kontakt
echo "✅ v$VERSION live!"
