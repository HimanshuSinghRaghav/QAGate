# QT Gate

Automated QA scoring for sales calls — score the sale before it ships.

## Understand the project (Obsidian)

Do **not** start by reading the whole repo. Open the knowledge vault in Obsidian:

1. Open Obsidian → **Open folder as vault** → `qt-gate/knowledge/`
2. Read **Home**, then **09 AI Context/START-HERE**
3. Then **01 Project/Overview** and **02 Architecture/Architecture**

That vault is the map: product, architecture, APIs, database, and scoring rules. Use it to understand *why* the gate exists before touching code.

Start here in the tree if you are not in Obsidian yet: [`knowledge/Home.md`](knowledge/Home.md) → [`knowledge/09 AI Context/START-HERE.md`](knowledge/09%20AI%20Context/START-HERE.md).

---

Monorepo layout (backend and frontend are siblings):

```
qt-gate/
  backend/     # FastAPI + Postgres scoring API
  web/         # Next.js dashboard + lead workspace
  knowledge/   # Obsidian vault — read this to understand the system
```

| Service | Directory | URL |
|---|---|---|
| API + Swagger | `backend/` | http://localhost:8000/docs |
| Web UI | `web/` | http://localhost:3000 |

## Quick start

**Backend** (terminal 1):

```bash
cd backend
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

Full seed / scripts / demo-audio docs: see [`backend/README.md`](backend/README.md).
