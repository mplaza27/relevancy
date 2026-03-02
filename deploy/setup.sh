#!/bin/bash
# Oracle Cloud Ubuntu setup script for Relevancy backend
# Run once after first SSH into the VM:
#   chmod +x deploy/setup.sh && ./deploy/setup.sh
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$REPO_DIR/deploy"

echo "=== Relevancy Oracle Cloud Setup ==="

# 1. System packages
echo "Installing system dependencies..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv python3-pip nginx certbot python3-certbot-nginx iptables-persistent

# 2. Open ports in iptables (Oracle Cloud has an extra firewall layer)
echo "Opening ports 80 and 443..."
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables-save | sudo tee /etc/iptables/rules.v4

# 3. Python venv
echo "Creating Python virtual environment..."
cd "$REPO_DIR"
python3.12 -m venv .venv
source .venv/bin/activate

# 4. Install backend
echo "Installing Python packages..."
pip install -e packages/anki_parser
pip install -e backend

# 5. Verify .env exists
if [ ! -f "backend/.env" ]; then
    echo ""
    echo "ERROR: backend/.env not found."
    echo "Create it from backend/.env.example and fill in DATABASE_URL + CORS_ORIGINS."
    exit 1
fi

# 6. Install systemd service
echo "Installing systemd service..."
sudo cp "$DEPLOY_DIR/relevancy.service" /etc/systemd/system/relevancy.service
# Update paths to match actual repo location
sudo sed -i "s|/home/ubuntu/relevancy|$REPO_DIR|g" /etc/systemd/system/relevancy.service
sudo systemctl daemon-reload
sudo systemctl enable relevancy
sudo systemctl start relevancy

# 7. Install nginx config
echo "Installing nginx config..."
sudo cp "$DEPLOY_DIR/nginx.conf" /etc/nginx/sites-available/relevancy
sudo ln -sf /etc/nginx/sites-available/relevancy /etc/nginx/sites-enabled/relevancy
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "=== Setup complete ==="
echo ""
echo "Check backend status:  sudo systemctl status relevancy"
echo "View backend logs:     sudo journalctl -u relevancy -f"
echo "Check health:          curl http://localhost:8000/health"
echo ""
echo "To enable HTTPS, run:"
echo "  sudo certbot --nginx -d your-domain.com"
