@alpstein-n8n-integration-engineer

Fix Alpstein n8n container to Alpstein backend connectivity only.

Context:
- HTTPS n8n is live at https://n8n.alpstein-ai.ch
- alpstein_n8n runs behind nginx on 127.0.0.1:15679
- Alpstein backend runs on host 0.0.0.0:8010
- Host can reach backend:
  http://127.0.0.1:8010/api/v1/health
  http://172.17.0.1:8010/api/v1/health
- alpstein_n8n currently times out reaching backend
- UFW may block Docker bridge → host traffic

Scope:
- networking fix only
- no workflow changes
- no backend code changes
- no nginx changes unless needed
- no public exposure of backend 8010
- do not touch integrationhubspot_n8n
- do not run Gate 1 yet

Tasks:
1. Inspect:
   - docker inspect alpstein_n8n network/gateway
   - ufw status verbose
   - relevant docker bridge subnet
   - current BACKEND_BASE_URL inside container

2. Prefer minimal safe fix:
   - allow only Alpstein Docker network/subnet to reach host tcp/8010
   - do not open 8010 publicly

3. Verify from inside alpstein_n8n:
   wget -qO- http://<working-host-gateway>:8010/api/v1/health

Expected:
{
  "success": true,
  "data": {
    "status": "ok",
    "service": "alpstein-ai-backend"
  }
}

4. Update docs only if needed:
   - docs/ops/n8n-runtime-start.md
   - docs/ops/n8n-https-reverse-proxy.md

Report:
- subnet/gateway used
- exact firewall/network rule added
- exact health response
- confirm 8010 is not publicly exposed
- confirm integrationhubspot_n8n untouched

Stop before workflow import/Gate 1.