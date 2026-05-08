# Matchmind Architecture

## Monorepo Boundaries

- `apps/api` owns server-side logic, secrets, provider integrations, Supabase access, and OpenAI calls.
- `apps/web` owns the browser experience and should only use public environment variables.
- `packages/shared` is reserved for shared contracts once the frontend and backend need them.

## Local Ports

- API: `http://localhost:8000`
- Web: framework default, commonly `http://localhost:5173` for Vite or `http://localhost:3000` for Next.js.
