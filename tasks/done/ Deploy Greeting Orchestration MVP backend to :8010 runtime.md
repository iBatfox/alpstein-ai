@alpstein-backend-engineer

Deploy Greeting Orchestration MVP backend to :8010 runtime.

Context:
Greeting Orchestration MVP passed review.
Backend implementation accepted for Alpstein demo path.
Now deploy/restart backend so Telegram tests use the new greeting logic.

Scope:
- backend deploy/runtime only
- no DB migration
- no n8n workflow changes
- no prompt redesign
- no T13.6
- no secrets printed

Preconditions:
- Current backend runtime is alpstein-backend-8010.service
- It should load /opt/alpstein-ai/.env
- ALPSTEIN_AI_DATABASE_URL and N8N_BACKEND_API_TOKEN must remain available
- Do not expose env values

Tasks:
1. Inspect current git status and confirm greeting files are present.
2. Run focused tests:
   - greeting policy
   - language detection
   - greeting prompt builder
   - AI reply orchestration greeting wire
3. Run full pytest if practical.
4. Restart only backend :8010 runtime:
   - alpstein-backend-8010.service
5. Verify:
   - systemctl status alpstein-backend-8010.service
   - GET http://127.0.0.1:8010/api/v1/health → 200
   - direct POST /api/v1/webhook/message → 200
6. Verify logs:
   - no traceback
   - no DB auth error
   - no OpenAI config crash
7. Do not change n8n yet.

Return:
- git status summary
- tests run
- restart command used
- health result
- direct POST result
- log summary
- whether n8n switch/test may start

Important:
Do not print DB URL, tokens, OpenAI key, Telegram tokens, or passwords.
Do not modify database.
Do not run migrations.