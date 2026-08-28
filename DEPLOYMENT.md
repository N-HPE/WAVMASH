# WaveMash Deployment

## Architecture

| Component | Platform | Auto-deploy trigger |
|-----------|----------|---------------------|
| Backend (FastAPI) | [Render](https://dashboard.render.com) | Push to `main` |
| Frontend (Next.js) | [Vercel](https://vercel.com) | Push to `main` |
| Database / Auth | [Supabase](https://supabase.com/dashboard) | Manual migrations |

## Vercel (Frontend)

1. Import GitHub repo `N-HPE/WAVMASH` (or `Wavemash`) in Vercel
2. Set **Root Directory** to `web`
3. Add environment variables:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://wavmash-backend.onrender.com` |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://rmnlckdjplratsqhccxk.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase Dashboard → Settings → API → anon key |

4. Deploy — every push to `main` triggers a new Vercel build

## Render (Backend)

Backend service `wavmash-backend` watches `main` with `autoDeploy: true`.

Required env vars (Render Dashboard → wavmash-backend → Environment):

- `SUPABASE_URL`
- `SUPABASE_KEY` / `SUPABASE_SERVICE_ROLE_KEY`
- `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET`
- `CORS_ORIGINS` — include your Vercel domain (e.g. `https://wavmash.vercel.app`)

## Local development

```bash
# Backend
cd server && uvicorn main:app --reload

# Frontend
cd web && npm run dev
```

Copy `web/.env.local.example` to `web/.env.local` and fill in values.
