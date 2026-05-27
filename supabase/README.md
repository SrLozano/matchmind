# Supabase Migrations

This folder contains versioned database changes for Matchmind.

The first migration is a baseline for the current MVP schema. It is written to be idempotent, so it can be reviewed and applied to the existing Supabase project without dropping data.

## Security Posture

The frontend does not read or write product tables directly through the Supabase client. Browser clients authenticate with Supabase Auth, then call the FastAPI backend. The backend uses the Supabase service role key and enforces product rules such as chat limits, Stripe upgrades, and bet P&L calculation.

For that reason, the baseline migration:

- enables RLS on all product tables;
- revokes direct table access from `anon` and `authenticated`;
- grants table access to `service_role`;
- defines read-only user-scoped policies as guardrails if direct authenticated access is intentionally granted in the future.

Do not grant browser clients direct write access to `public.users`, `public.bet_tracker`, or referral tables without first moving the backend-only business rules into database policies or functions.

## Production Apply

Review the SQL first, then apply it from the Supabase SQL editor or Supabase CLI against the production project.

For the first production apply, prefer a dashboard backup before running the migration.
