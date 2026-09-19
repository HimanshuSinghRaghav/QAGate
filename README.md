# QT Gate

Monorepo layout (backend and frontend are siblings):

```
qt-gate/
  qa-gate/   # FastAPI + Postgres scoring API
  web/       # Next.js dashboard + lead workspace
```

| Service | Directory | URL |
|---|---|---|
| API + Swagger | `qa-gate/` | http://localhost:8000/docs |
| Web UI | `web/` | http://localhost:3000 |

## Quick start

**Backend** (terminal 1):

```bash
cd qa-gate
docker compose up -d db
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional: OPENROUTER_API_KEY
python -m app.seed.run
uvicorn app.main:app --reload --port 8000
```

**Frontend** (terminal 2):

```bash
cd web
npm install
cp .env.example .env.local    # NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm run dev
```

Full seed / scripts / demo-audio docs: see [`qa-gate/README.md`](qa-gate/README.md).
