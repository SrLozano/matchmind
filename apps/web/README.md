# Matchmind Web

Paste or scaffold the frontend app in this directory.

Suggested shape for a Vite, Next.js, Lovable, or v0 export:

```text
apps/web/
├── package.json
├── src/ or app/
├── public/
└── .env.example
```

Point the frontend at the local API:

```text
VITE_API_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Use only public browser-safe variables here. Keep `OPENAI_API_KEY`, Supabase service-role keys, Stripe secrets, and data-provider keys in the backend/root `.env`.
