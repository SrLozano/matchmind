# Referral Payout Review

Use this checklist before paying pub partner commissions. In-app commission values are estimates until manually validated.

## Eligibility Rules

A pub referral is payout-eligible only when all of these are true:

- `referral_codes.owner_type = 'bar_partner'`
- `referral_attributions.partner_id is not null`
- `referral_attributions.conversion_source = 'stripe_checkout_completed'`
- `referral_attributions.stripe_checkout_session_id is not null`
- `referral_attributions.stripe_payment_intent_id is not null`
- `referral_attributions.converted_at is not null`
- `referral_attributions.payout_status = 'pending'`

Exclude duplicate accounts, fake referrals, self-referrals, suspicious activity, disputed payments, and cancelled payouts.

## Pending Pub Payout Summary

```sql
select
  rp.id as partner_id,
  rp.business_name,
  rp.responsible_name,
  rp.phone,
  rc.code,
  count(*) as verified_paid_referrals,
  sum(coalesce(ra.commission_amount, 0)) as estimated_commission,
  sum(coalesce(ra.gross_amount, 0)) as referred_revenue,
  min(ra.converted_at) as first_conversion_at,
  max(ra.converted_at) as latest_conversion_at
from referral_attributions ra
join referral_codes rc on rc.id = ra.referral_code_id
join referral_partners rp on rp.id = ra.partner_id
where rc.owner_type = 'bar_partner'
  and ra.partner_id is not null
  and ra.conversion_source = 'stripe_checkout_completed'
  and ra.stripe_checkout_session_id is not null
  and ra.stripe_payment_intent_id is not null
  and ra.converted_at is not null
  and ra.payout_status = 'pending'
group by rp.id, rp.business_name, rp.responsible_name, rp.phone, rc.code
order by estimated_commission desc, verified_paid_referrals desc;
```

## Detailed Rows For One Pub

Replace `CERVANTES` with the pub code under review.

```sql
select
  ra.id as attribution_id,
  ra.referred_user_id,
  u.email as referred_user_email,
  rc.code,
  rp.business_name,
  ra.converted_at,
  ra.gross_amount,
  ra.commission_amount,
  ra.payout_status,
  ra.stripe_checkout_session_id,
  ra.stripe_payment_intent_id,
  ra.converted_price_type,
  ra.payout_cancelled_at,
  ra.payout_cancellation_reason,
  ra.stripe_dispute_id
from referral_attributions ra
join referral_codes rc on rc.id = ra.referral_code_id
join referral_partners rp on rp.id = ra.partner_id
join users u on u.id = ra.referred_user_id
where rc.owner_type = 'bar_partner'
  and rc.code = 'CERVANTES'
order by ra.converted_at desc nulls last, ra.applied_at desc;
```

## Stripe Checks

For each payout batch, spot-check at least a few rows, and check every row if the total is small.

1. Search the `stripe_checkout_session_id` in Stripe.
2. Confirm Checkout Session status is complete and payment status is paid.
3. Confirm metadata `user_id` matches `referred_user_id`.
4. Confirm metadata `checkout_price_type` matches `converted_price_type`.
5. Search the `stripe_payment_intent_id` in Stripe.
6. Confirm PaymentIntent status is succeeded.
7. Confirm amount received matches `gross_amount`.
8. Confirm currency is EUR.
9. Confirm there is no dispute.
10. Confirm the payout row has `payout_status = 'pending'`.

If a payment has a dispute or the row is cancelled, do not pay commission for that attribution.

## Mark Reviewed Rows Approved

After manual review and before sending money:

```sql
update referral_attributions ra
set payout_status = 'approved'
from referral_codes rc
where rc.id = ra.referral_code_id
  and rc.owner_type = 'bar_partner'
  and rc.code = 'CERVANTES'
  and ra.conversion_source = 'stripe_checkout_completed'
  and ra.stripe_checkout_session_id is not null
  and ra.stripe_payment_intent_id is not null
  and ra.converted_at is not null
  and ra.payout_status = 'pending';
```

## Mark Rows Paid

After payment has actually been sent to the pub:

```sql
update referral_attributions ra
set payout_status = 'paid'
from referral_codes rc
where rc.id = ra.referral_code_id
  and rc.owner_type = 'bar_partner'
  and rc.code = 'CERVANTES'
  and ra.payout_status = 'approved';
```

## Cancel A Suspicious Row

Use this for manual fraud review, duplicate accounts, fake referrals, or suspicious activity:

```sql
update referral_attributions
set
  payout_status = 'cancelled',
  payout_cancelled_at = timezone('utc', now()),
  payout_cancellation_reason = 'manual_review'
where id = 'ATTRIBUTION_ID';
```

## Final Sanity Query

Run this before paying a pub. It should return only rows you intend to pay:

```sql
select
  ra.id,
  rc.code,
  rp.business_name,
  ra.commission_amount,
  ra.payout_status,
  ra.payout_cancellation_reason,
  ra.stripe_checkout_session_id,
  ra.stripe_payment_intent_id
from referral_attributions ra
join referral_codes rc on rc.id = ra.referral_code_id
join referral_partners rp on rp.id = ra.partner_id
where rc.owner_type = 'bar_partner'
  and rc.code = 'CERVANTES'
  and ra.payout_status in ('pending', 'approved')
order by ra.converted_at desc;
```
