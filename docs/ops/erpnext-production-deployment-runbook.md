# ERPNext Production Deployment Runbook (Phase F.1)

**Doc status:** ops / operator-runbook  
**Architecture:** [`f1-erpnext-installation-operational-architecture.md`](../architecture/f1-erpnext-installation-operational-architecture.md)  
**Public URL:** `https://crm.alpstein-ai.ch`  
**Server IP:** `144.91.113.184`  
**Decision:** ERPNext via **Docker** (`frappe_docker`), **host nginx** TLS

**Do not:** connect to Alpstein PostgreSQL, modify `alpstein-ai` compose, touch HubSpot n8n (`15678`).

---

## F.1.1 Preflight

```bash
# DNS (from any machine)
dig +short crm.alpstein-ai.ch
# expect: 144.91.113.184

# On server — capacity
free -h
df -h /
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
# Confirm alpstein stack healthy; note available RAM (target ≥4GB free for ERP)

# Confirm HubSpot n8n untouched
docker ps --filter name=integrationhubspot_n8n
```

**Minimum host recommendation (shared with Alpstein):** 12–16 GB RAM total, 80+ GB free disk.

---

## F.1.2 Install Docker prerequisites (if missing)

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git ufw

# Docker CE (if not already installed for Alpstein)
if ! command -v docker >/dev/null; then
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  sudo usermod -aG docker "$USER"
fi

docker compose version
# expect v2.x (Alpstein uses `docker compose`, not legacy `docker-compose` for new stacks)
```

---

## F.1.3 Create ERPNext project directory

```bash
sudo mkdir -p /opt/alpstein-erpnext
sudo chown "$USER:$USER" /opt/alpstein-erpnext
cd /opt/alpstein-erpnext

# Pin frappe_docker release (check https://github.com/frappe/frappe_docker/releases)
export FRAPPE_DOCKER_TAG=v5.24.0
git clone --depth 1 --branch "$FRAPPE_DOCKER_TAG" https://github.com/frappe/frappe_docker.git .
```

---

## F.1.4 Secrets and environment (no secrets in git)

```bash
sudo mkdir -p /etc/alpstein
sudo touch /etc/alpstein/erpnext.env
sudo chmod 600 /etc/alpstein/erpnext.env
sudo chown root:root /etc/alpstein/erpnext.env
```

Edit `/etc/alpstein/erpnext.env` (operator fills values):

```bash
# Site
export SITENAME=crm.alpstein-ai.ch
export ADMIN_PASSWORD='REPLACE_WITH_STRONG_PASSWORD'

# Version pins — use frappe_docker documented tags for ERPNext v15
export ERPNEXT_VERSION=v15.55.0
export FRAPPE_VERSION=v15.55.0

# DB
export DB_PASSWORD='REPLACE_MARIADB_ROOT_PASSWORD'
export MYSQL_ROOT_PASSWORD="${DB_PASSWORD}"

# Redis (if required by your compose override)
export REDIS_CACHE_PASSWORD='REPLACE_REDIS_PASSWORD'
export REDIS_QUEUE_PASSWORD="${REDIS_CACHE_PASSWORD}"
export REDIS_SOCKETIO_PASSWORD="${REDIS_CACHE_PASSWORD}"
```

```bash
set -a
source /etc/alpstein/erpnext.env
set +a
```

---

## F.1.5 Compose stack (MariaDB + Redis + ERPNext)

Use frappe_docker production pattern. Example using published compose files (paths match upstream repo layout — verify after clone):

```bash
cd /opt/alpstein-erpnext

# Copy example env if present
cp -n example.env .env 2>/dev/null || true

# Create operator override for loopback publish + project name
cat > compose.alpstein.override.yaml <<'YAML'
name: alpstein-erpnext

services:
  frontend:
    ports:
      - "127.0.0.1:18080:8080"
    restart: unless-stopped

  db:
    restart: unless-stopped
    volumes:
      - erpnext_mariadb_data:/var/lib/mysql

  redis-cache:
    restart: unless-stopped

  redis-queue:
    restart: unless-stopped

  redis-socketio:
    restart: unless-stopped

  backend:
    restart: unless-stopped

  websocket:
    restart: unless-stopped

  queue-short:
    restart: unless-stopped

  queue-long:
    restart: unless-stopped

  scheduler:
    restart: unless-stopped

volumes:
  erpnext_mariadb_data:
  sites:
YAML
```

Start database and redis first (exact service names may vary — run `docker compose config` and adjust):

```bash
cd /opt/alpstein-erpnext
set -a && source /etc/alpstein/erpnext.env && set +a

# Pull pinned images
export COMPOSE_FILE="compose.yaml:overrides/compose.mariadb.yaml:overrides/compose.redis.yaml:compose.alpstein.override.yaml"
docker compose -p alpstein-erpnext pull

# Start infrastructure
docker compose -p alpstein-erpnext up -d db redis-cache redis-queue
sleep 30
docker compose -p alpstein-erpnext ps
```

Create site (one-time; command from frappe_docker docs — adjust service name `backend` if different):

```bash
docker compose -p alpstein-erpnext run --rm backend bench new-site "${SITENAME}" \
  --mariadb-root-password "${DB_PASSWORD}" \
  --admin-password "${ADMIN_PASSWORD}" \
  --install-app erpnext \
  --no-mariadb-socket

# Set default site
docker compose -p alpstein-erpnext run --rm backend bench --site "${SITENAME}" set-config host_name "https://${SITENAME}"
docker compose -p alpstein-erpnext run --rm backend bench --site "${SITENAME}" set-config nginx_proxy true
```

Start full stack:

```bash
docker compose -p alpstein-erpnext up -d
docker compose -p alpstein-erpnext ps
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18080/
# expect 200 or 302 to login
```

**Verify no public bind:**

```bash
ss -tlnp | grep -E '18080|3306|6379|8080'
# 18080 should be 127.0.0.1 only; 3306/6379 should NOT appear on 0.0.0.0
```

---

## F.1.6 Host nginx + HTTPS

```bash
sudo tee /etc/nginx/sites-available/crm.alpstein-ai.ch <<'NGINX'
server {
    listen 80;
    listen [::]:80;
    server_name crm.alpstein-ai.ch;

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name crm.alpstein-ai.ch;

    # certbot will inject ssl_certificate paths
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:18080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/crm.alpstein-ai.ch /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

sudo certbot --nginx -d crm.alpstein-ai.ch --non-interactive --agree-tos --redirect \
  -m admin@alpstein-ai.ch
```

---

## F.1.7 Firewall

```bash
sudo ufw status verbose
# Ensure 80/443 allowed; ERP ports NOT opened
sudo ufw deny 18080/tcp comment 'ERPNext loopback only'
sudo ufw deny 8080/tcp
sudo ufw deny 3306/tcp
sudo ufw deny 6379/tcp
```

---

## F.1.8 Verification

```bash
curl -I http://crm.alpstein-ai.ch/
# expect 301 → https

curl -I https://crm.alpstein-ai.ch/
# expect 200 or 302

# From browser: login as Administrator (password from erpnext.env)

# Alpstein regression (must still pass)
curl -sS http://127.0.0.1:15679/healthz 2>/dev/null || true
curl -sS http://127.0.0.1:8010/api/v1/health 2>/dev/null || true
docker ps --filter name=alpstein_postgres --filter name=alpstein_backend --filter name=alpstein_n8n
```

Record results in § Evidence below.

---

## F.1.9 First backup

```bash
sudo mkdir -p /var/backups/erpnext/daily
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)

docker compose -p alpstein-erpnext exec -T db mariadb-dump -u root -p"${DB_PASSWORD}" --all-databases \
  | gzip > "/var/backups/erpnext/daily/mariadb-${BACKUP_DATE}.sql.gz"

docker run --rm \
  -v alpstein-erpnext_sites:/sites:ro \
  -v /var/backups/erpnext/daily:/backup \
  alpine tar czf "/backup/sites-${BACKUP_DATE}.tar.gz" -C /sites .

ls -lh /var/backups/erpnext/daily/
```

Optional cron (operator):

```cron
0 2 * * * root /opt/alpstein-erpnext/scripts/backup-erpnext.sh
```

---

## F.1.10 Upgrade procedure (reference)

```bash
cd /opt/alpstein-erpnext
# 1. Backup (F.1.9)
# 2. Edit /etc/alpstein/erpnext.env — bump ERPNEXT_VERSION / FRAPPE_VERSION
set -a && source /etc/alpstein/erpnext.env && set +a
docker compose -p alpstein-erpnext pull
docker compose -p alpstein-erpnext up -d
docker compose -p alpstein-erpnext exec backend bench --site "${SITENAME}" migrate
docker compose -p alpstein-erpnext exec backend bench --site "${SITENAME}" clear-cache
curl -I https://crm.alpstein-ai.ch/
```

Rollback: stop stack → restore `mariadb-*.sql.gz` + `sites-*.tar.gz` → previous image tags in env → `up -d`.

---

## Evidence (operator fills after deploy)

| Check | Date | Result | Notes |
|-------|------|--------|-------|
| DNS `crm.alpstein-ai.ch` | 2026-05-29 | **PASS** | → `144.91.113.184` |
| HTTPS login | 2026-05-29 | **PASS** | `curl -I https://crm.alpstein-ai.ch/` → 200 login page |
| Loopback only `18080` | 2026-05-29 | **PASS** | `127.0.0.1:18080` only; no `0.0.0.0:8080` after removing `compose.noproxy.yaml` |
| Alpstein n8n health | 2026-05-29 | **PASS** | `15679/healthz` → 200 |
| Alpstein backend health | 2026-05-29 | **PASS** | `8000/api/v1/health` → 200 |
| First backup size | | **PENDING** | Operator § F.1.9 |
| Image tags pinned | 2026-05-29 | **PASS** | `frappe/erpnext:v15.69.2`, `mariadb:10.6` |

Full report: [`f1-1-erpnext-production-deployment-2026-05-29.md`](../audits/f1-1-erpnext-production-deployment-2026-05-29.md).

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| 502 from nginx | `curl http://127.0.0.1:18080/`; `docker compose -p alpstein-erpnext logs frontend backend` |
| Site not found | `bench --site list` inside backend container |
| Wrong URL in emails | `bench set-config host_name https://crm.alpstein-ai.ch` |
| OOM kills | `dmesg \| grep -i oom`; reduce MariaDB buffer pool or upgrade RAM |
| Cert errors | `sudo certbot renew --dry-run` |
