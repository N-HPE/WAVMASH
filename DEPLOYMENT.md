# WaveMash Deployment Pipeline

## Flow (automatic)

```
git push origin main
        │
        ├─► Vercel  (GitHub integration)  → https://wavmash.vercel.app
        ├─► Render  (autoDeploy: commit)  → https://wavmash-backend.onrender.com
        └─► GitHub Actions
              1) frontend-build
              2) post-deploy-smoke  (poll /health + frontend until live)
```

After Actions is **green**, hard-refresh the site — that deploy is live.

| Component | Platform | Trigger | URL |
|-----------|----------|---------|-----|
| Frontend | Vercel | Push `main` | https://wavmash.vercel.app |
| Backend | Render | Push `main` | https://wavmash-backend.onrender.com |
| Auth / DB | Supabase | Manual migrations | Project `WAVMASH` |

## One-time setup checklist

### Vercel
1. Project linked to `N-HPE/WAVMASH`
2. **Root Directory** = `web`
3. Production Branch = `main`
4. Env (Production + Preview):

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://wavmash-backend.onrender.com` |
| `NEXT_PUBLIC_SUPABASE_URL` | your Supabase URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | your anon key |

### Render (`wavmash-backend`)
- Auto-Deploy = **On** (commit / `main`)
- Secrets: `SUPABASE_*`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`
- `CORS_ORIGINS` includes `https://wavmash.vercel.app` (also in `render.yaml` default)

### Supabase Auth
- Site URL: `https://wavmash.vercel.app`
- Redirect URLs: `https://wavmash.vercel.app/**`, `http://localhost:3000/**`

### GitHub Actions (optional secret)
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — only needed so CI build matches prod; a placeholder works for compile-only.

## Monitor

- Actions: https://github.com/N-HPE/WAVMASH/actions
- Render: https://dashboard.render.com → `wavmash-backend` → Events
- Vercel: https://vercel.com → Project → Deployments
- Live health: https://wavmash-backend.onrender.com/health

## Local

```bash
# Backend
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
npm --prefix web run dev
```
