# Stripe Payments

Matchmind uses Stripe Checkout for one payment product with referral-aware one-time prices:

- Product: World Cup Tournament Pass
- Standard price: EUR 9.99
- Founder price: EUR 6.99 until June 10, 2026 at 23:59 CEST
- Referral/Scout price: EUR 8.99
- Insider price: EUR 4.99
- Captain price: EUR 2.49
- Legend and Founder Circle price: free pass, activated by the API without Stripe Checkout
- Mode: one-time payment
- Result after successful payment: `public.users.plan = 'premium'`

Subscriptions, billing portal, refunds, invoices, and coupons are intentionally out of scope for the current implementation.

## Current Flow

```text
Profile upgrade button
-> POST /payments/create-checkout-session with Supabase bearer token
-> FastAPI creates a Stripe Checkout Session in payment mode
-> Stripe Checkout collects the location details needed for Stripe Tax calculations
-> user pays on Stripe-hosted Checkout
-> Stripe sends checkout.session.completed to /payments/webhook
-> FastAPI verifies Stripe-Signature against STRIPE_WEBHOOK_SECRET
-> FastAPI updates public.users.plan = 'premium'
-> FastAPI writes Stripe proof to referral_attributions when the user had applied a referral code
-> Later dispute/cancel webhooks can cancel unpaid referral payouts
-> frontend reloads /users/me on focus/profile refresh
```

The frontend never receives Stripe secret keys. It only receives the Checkout URL returned by the backend.

Referral commissions are based on Stripe-backed conversions, not `converted_at` alone. A paid referral must include `conversion_source = 'stripe_checkout_completed'`, a `stripe_checkout_session_id` written after signature verification, and `payout_status != 'cancelled'`; the webhook also stores `stripe_payment_intent_id`, `converted_price_type`, and `gross_amount` when Stripe provides them.

For v1, Matchmind does not offer refunds, but the webhook handles `charge.dispute.created` and `payment_intent.canceled` by cancelling unpaid referral payouts for the matching PaymentIntent. Already paid commissions are left unchanged for manual review.

Before paying pub partner commissions, use [Referral Payout Review](referral-payout-review.md). Pub commission values shown in the app are estimates until Stripe proof, referral legitimacy, and payout status have been manually reviewed.

## Backend Environment

Set these in the root/backend `.env`, not in `apps/web/.env.local`.

```text
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_TOURNAMENT_PASS_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_FOUNDER_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_REFERRAL_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_INSIDER_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_CAPTAIN_PRICE_ID=price_...
FOUNDER_PASS_SALE_ENDS_AT=2026-06-10T21:59:59+00:00
APP_URL=http://localhost:3000
```

| Variable | Local test value | Purpose |
|---|---|---|
| `STRIPE_SECRET_KEY` | `sk_test_...` | Server-side Stripe API key used to create Checkout Sessions. |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` from `stripe listen` | Secret used to verify that webhook events came from Stripe. |
| `STRIPE_TOURNAMENT_PASS_PRICE_ID` | `price_...` | Stripe Price ID for the one-time EUR 9.99 tournament pass. |
| `STRIPE_TOURNAMENT_PASS_FOUNDER_PRICE_ID` | `price_...` | Stripe Price ID for the one-time EUR 6.99 founder tournament pass. |
| `STRIPE_TOURNAMENT_PASS_REFERRAL_PRICE_ID` | `price_...` | Stripe Price ID for the one-time EUR 8.99 tournament pass shown for applied referral codes and Scout tier. |
| `STRIPE_TOURNAMENT_PASS_INSIDER_PRICE_ID` | `price_...` | Stripe Price ID for the one-time EUR 4.99 Insider referral tier. |
| `STRIPE_TOURNAMENT_PASS_CAPTAIN_PRICE_ID` | `price_...` | Stripe Price ID for the one-time EUR 2.49 Captain referral tier. |
| `FOUNDER_PASS_SALE_ENDS_AT` | `2026-06-10T21:59:59+00:00` | UTC expiry for the public founder price. This is 23:59 CEST on June 10, 2026. |
| `APP_URL` | `http://localhost:3000` | Success and cancel redirect base URL. |

Use the Price ID that starts with `price_`, not the Product ID that starts with `prod_`.

## Local Test-Mode Setup

1. In the Stripe Dashboard, make sure you are in test mode or sandbox mode.

2. Go to Developers -> API keys and copy the test secret key:

```text
STRIPE_SECRET_KEY=sk_test_...
```

3. Create the product:

- Name: `Matchmind World Cup Tournament Pass`
- Pricing model: one-off
- Standard price: EUR 9.99
- Currency: EUR

4. Add founder and referral one-off prices to the same product:

- Founder price: EUR 6.99
- Referral/Scout price: EUR 8.99
- Insider price: EUR 4.99
- Captain price: EUR 2.49
- Currency: EUR

Do not encode the bar code or discount in the Stripe Price name. Keep the product generic; Matchmind decides whether the user gets the referral price.

5. Copy the generated Price IDs:

```text
STRIPE_TOURNAMENT_PASS_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_FOUNDER_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_REFERRAL_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_INSIDER_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_CAPTAIN_PRICE_ID=price_...
FOUNDER_PASS_SALE_ENDS_AT=2026-06-10T21:59:59+00:00
```

6. Set the local app URL:

```text
APP_URL=http://localhost:3000
```

7. Install and log in to the Stripe CLI:

```bash
brew install stripe/stripe-cli/stripe
stripe login
```

8. Start webhook forwarding in a separate terminal:

```bash
stripe listen --forward-to localhost:8000/payments/webhook
```

9. Copy the printed webhook signing secret into `.env`:

```text
STRIPE_WEBHOOK_SECRET=whsec_...
```

The `whsec_...` from `stripe listen` is for local CLI-forwarded events. It is different from any webhook secret created in the Stripe Dashboard.

10. Restart the API after changing `.env`:

```bash
make api-dev
```

11. Start the frontend:

```bash
pnpm web:dev
```

12. Before the founder sale expiry, sign in with Supabase Auth, open Profile, and click the upgrade button. Checkout should show EUR 6.99. After `FOUNDER_PASS_SALE_ENDS_AT`, Checkout should show EUR 9.99.

13. For referral purchases, apply a code or seed personal referral metrics before clicking the upgrade button. Checkout should show the best eligible price: EUR 6.99 founder price, EUR 8.99 referral price, EUR 4.99, or EUR 2.49. Free tiers should return to the app with Premium active without opening Stripe Checkout.

14. Pay with Stripe's standard successful test card:

```text
4242 4242 4242 4242
```

Use any future expiry date, any CVC, and any postal code.

## Local Verification

Keep three terminals open:

```bash
make api-dev
```

```bash
stripe listen --forward-to localhost:8000/payments/webhook
```

```bash
pnpm web:dev
```

Expected success signs:

- Browser redirects from Matchmind to Stripe Checkout.
- Stripe Checkout returns to `http://localhost:3000/?payment=success`.
- The `stripe listen` terminal logs a delivered `checkout.session.completed` event.
- The API logs do not show an invalid signature error.
- The current user's row in Supabase changes to `plan = 'premium'`.
- If the user applied a referral code, their `public.referral_attributions` row gets `converted_at`, `conversion_source`, `stripe_checkout_session_id`, optional `stripe_payment_intent_id`, `converted_price_type`, and `gross_amount`. The partner dashboard only counts it as paid when the Stripe proof fields are present and `payout_status` is not `cancelled`.
- Profile shows the premium state after refresh or window focus.

Run automated checks before committing payment changes:

```bash
make api-test
pnpm --filter @matchmind/web exec tsc --noEmit
pnpm --filter @matchmind/web build
```

## Troubleshooting

### Checkout Does Not Open

Check:

- The user is signed in with Supabase Auth.
- The API is running at `NEXT_PUBLIC_API_URL`.
- `STRIPE_SECRET_KEY` starts with `sk_test_`.
- `STRIPE_TOURNAMENT_PASS_PRICE_ID` starts with `price_`.
- If the founder sale is active, `STRIPE_TOURNAMENT_PASS_FOUNDER_PRICE_ID` starts with `price_`.
- If testing discounted checkout, the matching `STRIPE_TOURNAMENT_PASS_REFERRAL_PRICE_ID`, `STRIPE_TOURNAMENT_PASS_INSIDER_PRICE_ID`, or `STRIPE_TOURNAMENT_PASS_CAPTAIN_PRICE_ID` starts with `price_`.
- The API was restarted after editing `.env`.

### Webhook Does Not Upgrade The User

Check:

- `stripe listen --forward-to localhost:8000/payments/webhook` is still running.
- `STRIPE_WEBHOOK_SECRET` matches the `whsec_...` printed by the current `stripe listen` process.
- The event type is `checkout.session.completed`.
- The Checkout Session metadata contains `user_id`.
- The user exists in `public.users`.

### Invalid Webhook Signature

Use the exact webhook signing secret for the source of the event:

- Local Stripe CLI forwarding: use the `whsec_...` printed by `stripe listen`.
- Dashboard webhook endpoint: use that endpoint's signing secret from the Dashboard.

Do not mix those two secrets. Stripe signs each delivery against the secret for the specific endpoint or CLI listener.

The backend intentionally reads the raw request body before calling `stripe.Webhook.construct_event(...)`; do not change the webhook route to parse JSON before signature verification.

### User Returns But Still Looks Free

The webhook may still be processing or may not have been delivered. Refresh Profile or switch away and back to the app window. If the plan still says free, inspect the Stripe CLI terminal and the Supabase `public.users` row.

## Production Checklist

Do not switch to live mode until local test-mode checkout and webhook delivery are reliable.

1. Create the live Stripe product and one-time EUR 9.99, EUR 6.99, EUR 8.99, EUR 4.99, and EUR 2.49 Prices in live mode.

2. Set production backend environment variables:

```text
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_TOURNAMENT_PASS_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_FOUNDER_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_REFERRAL_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_INSIDER_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_CAPTAIN_PRICE_ID=price_...
FOUNDER_PASS_SALE_ENDS_AT=2026-06-10T21:59:59+00:00
APP_URL=https://your-production-domain.com
```

3. In the Stripe Dashboard, create a production webhook endpoint:

```text
https://your-api-domain.com/payments/webhook
```

4. Subscribe the endpoint to:

```text
checkout.session.completed
charge.dispute.created
payment_intent.canceled
```

5. Copy that endpoint's signing secret into production `STRIPE_WEBHOOK_SECRET`.

6. Confirm the production API receives HTTPS traffic at `/payments/webhook`. Stripe requires HTTPS for live webhook endpoints.

7. Confirm CORS allows the production frontend origin through `CORS_ALLOWED_ORIGINS`.

8. In Stripe Tax settings, confirm the product tax code and use tax-inclusive pricing so the advertised consumer price remains the final amount charged. Add only tax registrations that have already been completed with the relevant tax authority.

9. Confirm the production frontend has only public browser-safe env vars:

```text
NEXT_PUBLIC_API_URL=https://your-api-domain.com
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=...
```

10. Run a live low-risk purchase only after confirming product, price, redirect URL, webhook endpoint, Stripe Tax settings, and Supabase production project are all correct.

11. After launch, monitor Stripe webhook deliveries and API logs. Webhook retries should be safe because setting `plan = 'premium'` repeatedly is idempotent for this v1 flow.

## Official Stripe References

- Stripe CLI: https://docs.stripe.com/stripe-cli/use-cli
- Webhooks and signature verification: https://docs.stripe.com/webhooks
- Signature troubleshooting: https://docs.stripe.com/webhooks/signature
- Test cards: https://docs.stripe.com/testing
