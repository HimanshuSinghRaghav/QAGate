# QA Gate — web UI

Next.js frontend. Lives as a **sibling** of the backend:

```
qt-gate/
  qa-gate/   # FastAPI backend
  web/       # this app
```

Full setup: [`../README.md`](../README.md) and [`../qa-gate/README.md`](../qa-gate/README.md).

```bash
# API must already be on :8000 (from ../qa-gate)
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm install
npm run dev                  # http://localhost:3000
```

Demo call audio is read from `../qa-gate/demo/audio/<leadId>.mp3`.
