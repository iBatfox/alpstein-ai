@alpstein-n8n-integration-engineer

Implement n8n HTTPS reverse proxy only.

Goal:
Expose project-local Alpstein n8n via HTTPS at https://n8n.alpstein-ai.ch.

Context:
- DNS is ready:
  n8n.alpstein-ai.ch -> 144.91.113.184
- alpstein_n8n is running locally on:
  127.0.0.1:15679 -> container 5678
- Do not touch integrationhubspot_n8n.
- Do not expose 15679 publicly.

Scope:
- nginx site config
- certbot SSL
- HTTP → HTTPS redirect
- websocket/proxy headers for n8n
- basic auth remains handled by n8n
- no workflow JSON changes
- no backend code changes
- no n8n compose changes unless required for public URL vars

Tasks:
1. Inspect existing nginx setup:
   - nginx -t
   - ls /etc/nginx/sites-available
   - ls /etc/nginx/sites-enabled
   - check existing alpstein-ai.ch config

2. Create nginx server block for:
   n8n.alpstein-ai.ch

Proxy target:
   http://127.0.0.1:15679

Required headers:
   proxy_set_header Host $host;
   proxy_set_header X-Real-IP $remote_addr;
   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   proxy_set_header X-Forwarded-Proto $scheme;
   proxy_http_version 1.1;
   proxy_set_header Upgrade $http_upgrade;
   proxy_set_header Connection "upgrade";

3. Enable site and validate:
   nginx -t
   systemctl reload nginx

4. Run certbot for:
   n8n.alpstein-ai.ch

5. Verify:
   curl -I http://n8n.alpstein-ai.ch
   curl -I https://n8n.alpstein-ai.ch
   browser login works

6. Security:
   - keep n8n bound to 127.0.0.1:15679
   - do not open raw 15679 publicly
   - do not print credentials
   - do not disable n8n basic auth

7. Docs:
   - create/update docs/ops/n8n-https-reverse-proxy.md
   - update docs/project-status/next-steps.md
   - update completed.md if successful

Report:
- nginx config path
- certbot result
- curl status codes
- whether browser login works
- confirm integrationhubspot_n8n untouched

Stop before changing workflows.