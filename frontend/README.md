# Frontend (Practicum EMR)

React + TypeScript + Vite + MUI UI for the UTEP Practicum EMR.

- Dev server: `npm run dev` → http://localhost:5173 (proxies `/api` → FastAPI `:8000`)
- Live API is the default; set `VITE_USE_MOCK=true` only for offline mock mode
- Vercel: Root Directory = `frontend` (see `vercel.json`). Set `VITE_API_URL` to the hosted API origin, or `VITE_USE_MOCK=true` for UI-only previews. Details in the **[root README](../README.md#deploy-vercel--frontend)**.

For setup, demo logins, MFA (`123456`), and the full walkthrough, see the **[root README](../README.md)**.
