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

## New Table Grants

Supabase is changing the default Data API exposure for new `public` tables. Do not rely on implicit table access when adding migrations.

Every migration that creates a new product table in `public` must explicitly set the intended privileges. Matchmind's default posture is:

- revoke direct access from `anon` and `authenticated`;
- grant only the required table privileges to `service_role`;
- keep browser access routed through FastAPI unless the product rules have been moved into RLS policies or database functions.

Use the narrowest `service_role` grant that matches the backend behavior. For example:

```sql
revoke all on public.example_table from anon, authenticated;
grant select, insert, update on public.example_table to service_role;
```

## Production Apply

Review the SQL first, then apply it from the Supabase SQL editor or Supabase CLI against the production project.

For the first production apply, prefer a dashboard backup before running the migration.
