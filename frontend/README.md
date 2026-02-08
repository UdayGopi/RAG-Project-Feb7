# React Chat Frontend

Redesigned chat UI for the RAG app. Tech stack: **React 18**, **Vite**, **react-markdown**.

## Run

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/chat`, `/health`, `/tenants`, `/upload` to the backend (default `http://localhost:5001`).

## Backend

- **Sync (Flask):** `python app.py` → port 5001  
- **Async (FastAPI):** `uvicorn api_async:app --host 0.0.0.0 --port 5002`

To use async API on port 5002, either:

1. Change Vite proxy in `vite.config.js` so `/chat` etc. point to `http://localhost:5002`, or  
2. Set `VITE_API_URL=http://localhost:5002` and run `npm run dev` (requests will go to 5002).

## Build

```bash
npm run build
```

Output is in `dist/`. Serve with any static host or point Flask to `dist/index.html` and serve `dist/` as static.
