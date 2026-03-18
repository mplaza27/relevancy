# Oracle Cloud — Manual Setup Steps

Instance is already running at `<ORACLE_IP>`. The repo has not been cloned yet and no services are configured.

## 1. SSH in

```bash
ssh ubuntu@<ORACLE_IP>
```

## 2. Open firewall ports

Oracle instances have a host-level iptables firewall in addition to the VCN security list. Open ports 80 and 443:

```bash
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

Also verify ports 80 and 443 are open in Oracle Console → Networking → Virtual Cloud Networks → your VCN → Security Lists → Ingress Rules.

## 3. Install system dependencies

Ubuntu 22.04 doesn't include Python 3.12 in its default repos — install `software-properties-common` first, then add the deadsnakes PPA:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip git nginx certbot python3-certbot-nginx
```

When prompted to restart services, select `21` (none of the above) — you can reboot at the end.

## 4. Clone the repo

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/relevancy.git
cd relevancy
```

## 5. Install Python dependencies

uv workspace support is unreliable on the server — use pip with a standard venv instead:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e packages/anki_parser -e backend
```

## 6. Create the .env file

`nano` and `vi` are not installed on the minimal image. Use Python to write the file:

```bash
cp backend/.env.example backend/.env
python3.12 -c "
import pathlib
env = pathlib.Path('backend/.env').read_text()
env = env.replace('your-password', 'YOUR_PASSWORD')
env = env.replace('xxxxxxxxxxxx', 'YOUR_PROJECT_REF')
pathlib.Path('backend/.env').write_text(env)
print('Done')
"
```

Replace `YOUR_PASSWORD` and `YOUR_PROJECT_REF` with your real Supabase credentials before running.

## 7. Test the backend manually

```bash
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend
```

Wait for the model to load, then in another terminal:

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","model_loaded":true,"db_connected":true}
```

Press `Ctrl+C` to stop before moving on.

## 8. Set up systemd service

```bash
sudo tee /etc/systemd/system/relevancy.service << 'EOF'
[Unit]
Description=Relevancy Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/relevancy
Environment=PATH=/home/ubuntu/relevancy/.venv/bin:/usr/local/bin:/usr/bin
ExecStart=/home/ubuntu/relevancy/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable relevancy
sudo systemctl start relevancy
sudo systemctl status relevancy
```

## 9. Configure nginx

```bash
sudo tee /etc/nginx/sites-available/relevancy << 'EOF'
server {
    listen 80;
    server_name <ORACLE_IP>;

    client_max_body_size 55M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/relevancy /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

## 10. Verify from your local machine

```bash
curl http://<ORACLE_IP>/health
# Expected: {"status":"ok","model_loaded":true,"db_connected":true}
```

## 11. SSL (if you have a domain pointed at the server)

```bash
sudo certbot --nginx -d your-domain.com
```

If using only the raw IP, skip this step — browsers will warn about HTTP but it will still work.

## Logs & maintenance

```bash
# Live backend logs
sudo journalctl -u relevancy -f

# Restart after a git pull
cd ~/relevancy
git pull
.venv/bin/pip install -e packages/anki_parser -e backend
sudo systemctl restart relevancy
```

## Checklist

- [x] iptables ports 80/443 open
- [x] VCN security list ports 80/443 open
- [x] System dependencies installed
- [x] Repo cloned to `~/relevancy`
- [x] `backend/.env` filled in with real Supabase credentials
- [x] `curl http://localhost:8000/health` returns ok
- [x] systemd service enabled and running
- [x] nginx proxying traffic on port 80
- [x] `curl http://<ORACLE_IP>/health` returns ok from local machine
