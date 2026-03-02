# Relevancy — Manual Deployment Steps

Everything in the repo is code-complete. These are the three human steps needed to go live.

---

## Step 1 — Supabase (Database + Embeddings)

### 1a. Create a Supabase project
1. Go to [https://supabase.com](https://supabase.com) → sign in → **New project**
2. Choose a name (e.g. `relevancy`) and the region closest to you
3. Set a strong database password and save it somewhere safe
4. Wait ~2 minutes for the project to provision

### 1b. Get your connection string
In the Supabase dashboard:
- **Settings → Database → Connection string → URI tab**
- Select **Session mode** (NOT Transaction mode) and copy the string
- It looks like: `postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres`

> **Critical:** Use port **5432** (direct), never **6543** (pooler). The pooler breaks asyncpg prepared statements.

### 1c. Run the schema
1. In the Supabase dashboard, go to **SQL Editor → New query**
2. Paste the entire contents of `sql/schema.sql`
3. Click **Run**

Verify it worked:
```sql
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
-- Should show: anki_notes, upload_sessions, document_chunks, match_results
```

### 1d. Pre-compute embeddings (run locally on your machine)
This is a one-time GPU job. Requires `anking/AnKing Step Deck.apkg` in the repo root.

```bash
# From repo root
source .venv/bin/activate
pip install sentence-transformers torch  # if not already installed

python scripts/precompute_embeddings.py
# Output: scripts/output/embeddings.jsonl (~28,660 lines)
# Takes ~5-15 minutes on a 3080
```

Check it worked:
```bash
wc -l scripts/output/embeddings.jsonl
# Should be ~28660
head -1 scripts/output/embeddings.jsonl | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['embedding']), 'dims')"
# Should print: 384 dims
```

### 1e. Upload embeddings to Supabase
```bash
# From repo root
pip install psycopg psycopg-binary pgvector  # if not already in scripts/requirements.txt

export DATABASE_URL="postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres"

python scripts/upload_to_supabase.py
# Takes ~5-10 minutes, prints progress
# Done when: "Inserted 28,660 rows"
```

Verify in Supabase SQL Editor:
```sql
SELECT COUNT(*) FROM anki_notes;
-- Should be ~28660

SELECT pg_size_pretty(pg_database_size('postgres'));
-- Should be ~130-150 MB (well under 500 MB free tier limit)
```

### 1f. Test vector search works
```sql
SELECT note_id, LEFT(text, 80), 1 - (embedding <=> (SELECT embedding FROM anki_notes LIMIT 1)) AS sim
FROM anki_notes
ORDER BY embedding <=> (SELECT embedding FROM anki_notes LIMIT 1)
LIMIT 5;
-- Top result sim = 1.0, rest < 1.0
```

---

## Step 2 — Oracle Cloud (Backend)

### 2a. Create an Oracle Cloud account
1. Go to [https://cloud.oracle.com](https://cloud.oracle.com) → **Start for free**
2. A credit card is required but **Always Free resources are never charged**
3. Choose your home region during signup — this cannot be changed later

### 2b. Provision a VM
1. Go to **Compute → Instances → Create Instance**
2. Configure:
   - **Name**: `relevancy`
   - **Shape**: Change shape → **Ampere** → `VM.Standard.A1.Flex` → set **4 OCPUs, 24 GB RAM**
   - **Image**: Ubuntu 22.04 (Minimal, aarch64)
   - **Boot volume**: 50 GB
   - **SSH keys**: paste your public key (`~/.ssh/id_rsa.pub` or `~/.ssh/id_ed25519.pub`)
3. Click **Create** and note the **public IP address**

### 2c. Open ports in Oracle's firewall
In the OCI dashboard, the VM lives inside a VCN that blocks ports by default.

Go to **Networking → Virtual Cloud Networks → your VCN → Security Lists → Default Security List → Add Ingress Rules**:

| Source CIDR | Protocol | Port |
|-------------|----------|------|
| 0.0.0.0/0 | TCP | 80 |
| 0.0.0.0/0 | TCP | 443 |

### 2d. SSH in and run the setup script
```bash
ssh ubuntu@<your-public-ip>

# Clone the repo
git clone https://github.com/your-username/relevancy.git
cd relevancy

# Create backend .env BEFORE running setup
cp backend/.env.example backend/.env
nano backend/.env
```

Fill in `backend/.env`:
```
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres
CORS_ORIGINS=["https://YOUR_FRONTEND_DOMAIN"]
```
> Replace `YOUR_FRONTEND_DOMAIN` with your actual Cloudflare Pages URL (you'll get this in Step 3).
> If using a custom domain, add it too: `["https://YOUR_FRONTEND_DOMAIN","https://yourdomain.com"]`

```bash
# Run the automated setup (installs Python, nginx, systemd service)
chmod +x deploy/setup.sh
./deploy/setup.sh
```

### 2e. Verify the backend is running
```bash
# On the Oracle VM
sudo systemctl status relevancy     # should show: active (running)
curl http://localhost:8000/health
# Expected: {"status":"ok","model_loaded":true,"db_connected":true}

# From your local machine
curl http://<your-public-ip>/health
# Same response
```

If `model_loaded` is false, the model is still downloading on first boot. Wait 1-2 minutes and retry.

View logs:
```bash
sudo journalctl -u relevancy -f
```

### 2f. (Optional) SSL with a domain
If you have a domain pointed at the Oracle IP:
```bash
sudo certbot --nginx -d yourdomain.com
# Follow the prompts — auto-configures HTTPS + renewal
```

---

## Step 3 — Cloudflare Pages (Frontend)

### 3a. Push the repo to GitHub (if not already)
```bash
# From repo root, on your local machine
git remote add origin https://github.com/your-username/relevancy.git
git push -u origin master
```

### 3b. Create a Cloudflare Pages project
1. Go to [https://dash.cloudflare.com](https://dash.cloudflare.com) → **Pages → Create a project → Connect to Git**
2. Authorize GitHub and select the `relevancy` repo
3. Configure the build:
   - **Build command**: `cd frontend && npm install && npm run build`
   - **Build output directory**: `frontend/dist`
4. Under **Environment variables**, add:
   - `VITE_API_URL` = `https://yourdomain.com` (or `http://<oracle-public-ip>` if no domain)
5. Click **Save and Deploy**

Cloudflare will build and deploy. You'll get a URL like `https://YOUR_FRONTEND_DOMAIN`.

### 3c. Update CORS on the backend
Now that you have the real Cloudflare URL, update `backend/.env` on the Oracle VM:

```bash
ssh ubuntu@<your-public-ip>
nano ~/relevancy/backend/.env
```

Update `CORS_ORIGINS`:
```
CORS_ORIGINS=["https://YOUR_FRONTEND_DOMAIN"]
```

Restart the backend:
```bash
sudo systemctl restart relevancy
curl http://localhost:8000/health   # verify still healthy
```

---

## Final Verification

Run these from your local machine once everything is deployed:

```bash
export BACKEND="https://yourdomain.com"   # or http://<oracle-ip>
export FRONTEND="https://YOUR_FRONTEND_DOMAIN"

# 1. Backend health
curl -sf "$BACKEND/health" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['model_loaded'] is True, 'model not loaded — wait and retry'
assert d['db_connected'] is True, 'check DATABASE_URL in backend/.env'
print('Backend: OK')
"

# 2. Note count
curl -sf "$BACKEND/api/stats" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Notes: {d[\"anki_note_count\"]:,}  DB: {d[\"db_size_mb\"]} MB')
assert d['anki_note_count'] >= 28000, 'embeddings not fully uploaded'
print('Supabase: OK')
"

# 3. CORS
curl -sf -X OPTIONS "$BACKEND/api/upload" \
  -H "Origin: $FRONTEND" \
  -H "Access-Control-Request-Method: POST" \
  -I 2>&1 | grep -i "access-control-allow-origin"
# Should print the frontend origin

# 4. Frontend loads
curl -sf "$FRONTEND" | grep -q "Relevancy" && echo "Frontend: OK" || echo "FAIL: check Cloudflare build logs"
```

If all four pass, the project is live. Fill in `tests/deployed-test-report.md` with results.

---

## Quick Reference

| What | Where |
|------|-------|
| Schema SQL | `sql/schema.sql` |
| Embeddings script | `scripts/precompute_embeddings.py` |
| Upload script | `scripts/upload_to_supabase.py` |
| Supabase verify SQL | `scripts/verify_supabase.sql` |
| Backend env template | `backend/.env.example` |
| Frontend env template | `frontend/.env.example` |
| Oracle setup script | `deploy/setup.sh` |
| Systemd service | `deploy/relevancy.service` |
| Nginx config | `deploy/nginx.conf` |
| Deployed test report | `tests/deployed-test-report.md` |
