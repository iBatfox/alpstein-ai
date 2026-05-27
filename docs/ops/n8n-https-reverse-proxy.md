**Doc status:** runtime-derived  
**Tier:** ops/production (pending move)

# n8n HTTPS Reverse Proxy (Alpstein)

**Domain:** `https://n8n.alpstein-ai.ch`  
**Upstream:** `http://127.0.0.1:15679` → container `alpstein_n8n` (localhost only)  
**Runtime:** [`n8n-runtime-start.md`](n8n-runtime-start.md) · [`n8n-deployment-plan.md`](n8n-deployment-plan.md)

HubSpot n8n remains on **`/etc/nginx/sites-available/n8n.conf`** → `127.0.0.1:15678` (`integrationhubspot_n8n`). **Do not edit that file.**

---

## Nginx config (server)

| Item | Path |
|------|------|
| Site config | `/etc/nginx/sites-available/n8n.alpstein-ai.ch` |
| Enabled link | `/etc/nginx/sites-enabled/n8n.alpstein-ai.ch` |
| SSL cert | `/etc/letsencrypt/live/n8n.alpstein-ai.ch/` |

Certbot manages HTTPS server block and HTTP→HTTPS redirect on this file.

### Proxy settings (Alpstein only)

```nginx
location / {
    proxy_pass http://127.0.0.1:15679;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    proxy_buffering off;
}
```

---

## Security

| Rule | Status |
|------|--------|
| `alpstein_n8n` bound to `127.0.0.1:15679` only | Yes — raw **15679** not public |
| nginx proxies HTTPS → `127.0.0.1:15679` | Yes — public entry is **443** only |
| Public access via nginx 80/443 only | Yes |
| n8n basic auth | Remains in n8n (not disabled in nginx) |
| `integrationhubspot_n8n` | Unchanged (`15678`, separate nginx site) |

---

## Certbot

```bash
sudo certbot --nginx -d n8n.alpstein-ai.ch --non-interactive --agree-tos --redirect
```

**Result (2026-05-25):** Certificate issued; expires **2026-08-23**; auto-renew scheduled.

---

## Verify

```bash
curl -I http://n8n.alpstein-ai.ch    # expect 301 → https://n8n.alpstein-ai.ch/
curl -I https://n8n.alpstein-ai.ch   # expect 200 (UI HTML via nginx)
docker ps --filter name=integrationhubspot_n8n --filter name=alpstein_n8n
ss -tlnp | grep 15679                 # expect 127.0.0.1 only
```

**Observed (2026-05-25):**

| Check | Result |
|-------|--------|
| HTTP | `301` → `https://n8n.alpstein-ai.ch/` |
| HTTPS | `200` |
| Port `15679` | `127.0.0.1` only |
| HubSpot `n8n.conf` | Still `proxy_pass http://127.0.0.1:15678` |

### Browser login

Open `https://n8n.alpstein-ai.ch` and sign in with **n8n basic auth** credentials from `/opt/alpstein-ai/n8n/.env` (`N8N_BASIC_AUTH_*`). Nginx does not terminate basic auth.

### n8n public URL env (HTTPS webhooks)

Set in **`/opt/alpstein-ai/n8n/.env`** (names only — no values in repo):

```env
N8N_HOST=n8n.alpstein-ai.ch
N8N_PROTOCOL=https
WEBHOOK_URL=https://n8n.alpstein-ai.ch/
```

Recreate container after changes:

```bash
cd /opt/alpstein-ai/n8n
docker-compose -p alpstein-n8n up -d
```

Editor test URL (Gate 1 verified): `https://n8n.alpstein-ai.ch/webhook-test/alpstein/test/incoming`

No workflow JSON changes required for proxy itself.

---

## Reload nginx (after manual edits)

```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## Related

- Workflow import: [`n8n-workflow1-test-webhook.md`](n8n-workflow1-test-webhook.md)
- Container→backend: `BACKEND_BASE_URL=http://172.20.0.1:8010` + UFW allow `172.20.0.0/16` → `8010` (see [`n8n-runtime-start.md`](n8n-runtime-start.md))
- Gate 1: **passed** (2026-05-25) — see [`n8n-workflow1-test-webhook.md`](n8n-workflow1-test-webhook.md); next **T13.4**
