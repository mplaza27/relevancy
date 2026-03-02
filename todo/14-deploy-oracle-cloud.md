[x]
# Prompt 14: Deployment — Oracle Cloud + Cloudflare Pages

## Goal
Deploy the backend to Oracle Cloud Always Free and the frontend to Cloudflare Pages for a $0/month production setup.

## Context
- Oracle Cloud Always Free: 4 ARM Ampere cores, 24GB RAM, 200GB storage (never expires)
- Cloudflare Pages: unlimited bandwidth, 500 builds/month (always free)
- Backend: FastAPI + sentence-transformers model (~150MB RAM when loaded)
- Frontend: Static React build served from CDN

## Part A: Oracle Cloud Backend

### 1. Create Oracle Cloud Account
1. Sign up at https://cloud.oracle.com (requires credit card but won't charge for Always Free)
2. Choose home region (closest to your users)

### 2. Create Always Free Compute Instance
1. Go to Compute > Instances > Create Instance
2. Select:
   - **Shape**: VM.Standard.A1.Flex (Ampere ARM)
   - **OCPUs**: 4 (max for Always Free)
   - **RAM**: 24 GB (max for Always Free)
   - **Image**: Ubuntu 22.04 or 24.04 (ARM)
   - **Boot volume**: 50 GB (Always Free includes up to 200GB)
3. Add your SSH public key
4. Create and note the public IP

### 3. Configure Network Security
In the VCN security list, add ingress rules:
- Port 80 (HTTP)
- Port 443 (HTTPS)
- Port 22 (SSH — already open by default)

Also open in the instance's iptables:
```bash
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

### 4. Install System Dependencies
```bash
# SSH into the instance
ssh ubuntu@<public-ip>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12+
sudo apt install -y python3.12 python3.12-venv python3-pip

# Install system deps for PyMuPDF
sudo apt install -y libmupdf-dev

# Install nginx as reverse proxy
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 5. Deploy Backend
```bash
# Clone the repo
git clone https://github.com/your-username/relevancey.git
cd relevancey

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install packages
pip install -e packages/anki_parser
pip install -e backend

# Create .env
cat > backend/.env << 'EOF'
DATABASE_URL=postgresql://postgres:password@db.xxxx.supabase.co:5432/postgres
CORS_ORIGINS=["https://relevancey.pages.dev","http://localhost:5173"]
EOF

# Test it works
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Ctrl+C after verifying
```

### 6. Set Up systemd Service
```bash
sudo tee /etc/systemd/system/relevancey.service << 'EOF'
[Unit]
Description=Relevancey Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/relevancey/backend
Environment=PATH=/home/ubuntu/relevancey/.venv/bin
ExecStart=/home/ubuntu/relevancey/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable relevancey
sudo systemctl start relevancey
sudo systemctl status relevancey
```

### 7. Configure Nginx Reverse Proxy
```bash
sudo tee /etc/nginx/sites-available/relevancey << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # or the Oracle Cloud public IP

    client_max_body_size 55M;  # slightly above 50MB upload limit

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;  # allow time for large file processing
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/relevancey /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

### 8. SSL with Let's Encrypt (if using a domain)
```bash
sudo certbot --nginx -d your-domain.com
```

## Part B: Cloudflare Pages Frontend

### 1. Build the Frontend
```bash
cd frontend

# Update API URL to production backend
echo "VITE_API_URL=https://your-domain.com" > .env.production

npm run build
# Output: frontend/dist/
```

### 2. Deploy to Cloudflare Pages

**Option A: Via Git (recommended)**
1. Push repo to GitHub
2. Go to Cloudflare Dashboard > Pages > Create a project
3. Connect to GitHub repo
4. Configure:
   - **Build command**: `cd frontend && npm install && npm run build`
   - **Build output directory**: `frontend/dist`
   - **Environment variable**: `VITE_API_URL=https://your-domain.com`
5. Deploy

**Option B: Direct upload**
```bash
npx wrangler pages deploy frontend/dist --project-name=relevancey
```

### 3. Custom Domain (Optional)
In Cloudflare Pages settings, add a custom domain. This also enables HTTPS automatically.

## Part C: DNS & CORS Configuration

### Update Backend CORS
In `backend/.env`, update `CORS_ORIGINS` to include the Cloudflare Pages URL:
```
CORS_ORIGINS=["https://relevancey.pages.dev","https://your-custom-domain.com"]
```

Restart the backend:
```bash
sudo systemctl restart relevancey
```

## Part D: Monitoring & Maintenance

### Health Check
```bash
# From your local machine
curl https://your-domain.com/health
# Should return: {"status": "ok", "model_loaded": true, "db_connected": true}
```

### Logs
```bash
# Backend logs
sudo journalctl -u relevancey -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log
```

### Updates
```bash
ssh ubuntu@<public-ip>
cd relevancey
git pull
source .venv/bin/activate
pip install -e packages/anki_parser
pip install -e backend
sudo systemctl restart relevancey
```

## Verification Checklist
- [ ] Oracle Cloud instance running (4 ARM cores, 24GB RAM)
- [ ] Backend accessible at `https://your-domain.com/health`
- [ ] Frontend loads at `https://relevancey.pages.dev` (or custom domain)
- [ ] Upload a PDF through the live site → get results
- [ ] Slider works, sync options work
- [ ] CORS configured correctly (no browser console errors)
- [ ] SSL working (HTTPS)
- [ ] Backend auto-restarts on crash (systemd)
- [ ] Total monthly cost: $0.00
