# Legal and Compliance Pass

Last updated: 2026-05-27

This is an operational product review, not legal advice. Before broad public launch or paid acquisition, Matchmind should still get a short review from a lawyer familiar with Spain/EU digital services and gambling-adjacent products.

## Current Product Position

Matchmind should remain a betting-analysis and decision-support tool:

- It does not accept bets.
- It does not place bets.
- It does not hold gambling balances or customer betting funds.
- It does not pay gambling winnings.
- It does not provide bookmaker affiliate links, bonuses, betslip links, or direct calls to place bets.
- It charges for access to analysis features, not for betting services.

This line matters because Spain's gambling framework regulates gambling activity, operators, licenses, and gambling-related commercial communications. The current product is intentionally outside bet execution, but it is still gambling-adjacent and should keep a conservative public posture.

## Sources Checked

- Spain gambling law reference: BOE, Ley 13/2011, de regulación del juego: https://www.boe.es/buscar/act.php?id=BOE-A-2011-9280
- Spain safer gambling / self-exclusion resource: DGOJ RGIAJ: https://www.ordenacionjuego.es/participantes-juego/juego-seguro/rgiaj
- Spain commercial communications reference: Real Decreto 958/2020: https://www.boe.es/buscar/act.php?id=BOE-A-2020-13495

## Minimum Launch Rules

1. Keep age gating at account creation: users confirm they are 18 or older.
2. Keep "analysis only / no guarantees / no bet placement" visible before signup and before checkout.
3. Keep responsible-use resources visible from the app and public legal pages.
4. Avoid language like "safe bet", "lock", "guaranteed", "risk-free", or "sure profit".
5. Avoid affiliate/deep links to bookmakers until a separate legal and product review is complete.
6. Avoid bookmaker bonuses, promotions, or operator-specific calls to action.
7. Keep referral rewards framed as Matchmind access discounts/commissions, not gambling incentives.
8. Make pub partner commissions manual-review-only until Stripe proof, referral legitimacy, and payout status are verified.
9. Keep all user betting logs manual; Matchmind must not sync or place bets with operators in v1.
10. Maintain a user support/contact route before charging real users.

## Changes Made In This Pass

- Added public Terms and Disclaimer page at `/legal/terms`.
- Added public Privacy Policy page at `/legal/privacy`.
- Added public Responsible Use page at `/legal/responsible-use`.
- Added Spanish legal pages at `/es/legal/terms`, `/es/legal/privacy`, and `/es/legal/responsible-use`.
- Added legal links to signup/signin surfaces.
- Added terms/privacy links to the upgrade checkout modal.
- Added legal routes to the sitemap.

## Still Needs Owner Action

- Add a real support/contact email to the app and legal pages before live payments.
- Decide company/legal entity name and billing identity before Stripe live mode.
- Ask counsel whether Matchmind's Spain-facing marketing copy and paid referral/pub partner program needs any additional disclaimer, restriction, or registration.
- Ask tax/accounting advice on VAT treatment for EU digital services before live Stripe payments.
