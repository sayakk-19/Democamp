# Local sign-in and payment setup

These changes affect the landing-page account button, social sign-in, and shop payment checkout. Existing passwords, approval rules, registration layout, and administrator pages are preserved. No private configuration file is read by the new integrations.

## Database setup

Two migrations are included and have **not** been applied to your existing database:

- `store/migrations/0016_socialidentity.py` stores provider account IDs linked to club accounts. It does not store provider access tokens or client secrets.
- `shop/migrations/0003_order_payment_state.py` adds payment references and states to existing orders. It does not remove existing fields or records.

After reviewing them, run in your own project terminal:

```powershell
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

## Local Paytm demo — no merchant credentials needed

On localhost, with Django `DEBUG=True`, checkout defaults to a local simulator. You can explicitly select it in the server's environment:

```powershell
$env:PAYTM_MODE = 'demo'
```

Add an available product to the cart, open `/shop/checkout/`, and enter the shipping fields. Place Order opens **LOCAL DEMO** checkout for `LOCAL_DEMO_MERCHANT`. The success, failure, and pending buttons simulate each result without contacting Paytm or a bank.

- The server recalculates prices from the product records; browser-supplied prices and totals cannot determine the charge.
- Outcomes are stored as `demo_paid`, `demo_failed`, or `demo_pending`. They are never recorded as a real `paid` transaction.
- Demo submissions require CSRF, a signed expiring order token, and the same browser session.
- Demo mode is blocked outside a loopback connection and when `DEBUG=False`.
- No real payment has been tested by this simulator. A fictional merchant ID/key cannot authenticate against Paytm's real sandbox.

## Google, GitHub, and X sign-in

The existing logos on registration and login now open authorization-code flows with state checking, PKCE, and a ten-minute local flow limit. A provider account must be registered with its provider before it can sign users into your application. Configure credentials privately in the environment used to start Django; do not paste them into chat or commit them to source.

| Provider | Runtime values | Exact callback when using `127.0.0.1:8000` |
| --- | --- | --- |
| Google | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | `http://127.0.0.1:8000/store/social/google/callback/` |
| GitHub | `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` | `http://127.0.0.1:8000/store/social/github/callback/` |
| X | `X_CLIENT_ID`, `X_CLIENT_SECRET` for a confidential web client | `http://127.0.0.1:8000/store/social/x/callback/` |

Register exactly the hostname you use in the browser: `localhost` and `127.0.0.1` are different callback origins. Optionally set the nonsecret `PUBLIC_BASE_URL` to that origin to keep callback URLs consistent. Use HTTPS for a deployed origin. X needs OAuth 2.0 enabled and access to `users.read`, `users.email`, and `tweet.read`; platform/API access is controlled by X. Public X clients can omit the secret, but a server-side confidential web client is preferred.

For a first-time social user, the application asks for the existing club profile fields and creates a pending club membership with an unusable local password. Normal administrator approval remains required. After approval, the same social logo signs that account in.

For an existing club account, the completion page asks for the club email and password once to explicitly connect the provider. A matching provider email alone does **not** connect or take over an existing club account. Later sign-ins use the provider's stable ID and the approved store session. Deleting the club account removes its provider links.

If provider credentials are missing, the login page explains that sign-in is not configured. It does not simulate a successful social login. Google/GitHub/X authorization cannot be tested end-to-end without your own provider app registration; no shared demo client credentials are included.

Official references: [Google](https://developers.google.com/identity/openid-connect/openid-connect), [GitHub](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps), [X](https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code).

## Real Paytm sandbox or production, when you choose to enable it

Configure the following **privately**, then restart Django:

| Value | Purpose |
| --- | --- |
| `PAYTM_MODE` | `staging` for Paytm test credentials, or `production` for activated production credentials |
| `PAYTM_MID` | Paytm-issued merchant ID; legacy runtime variable `MID` is also accepted |
| `PAYTM_MERCHANT_KEY` | Matching merchant key; legacy runtime variable `MERCHANT_KEY` is also accepted |
| `PAYTM_CALLBACK_URL` | Reachable HTTPS URL ending in `/shop/handlerequest/` |
| `PAYTM_WEBSITE_NAME` | Merchant website name; defaults to `WEBSTAGING` in staging and `DEFAULT` in production |

`PUBLIC_BASE_URL` can supply the HTTPS callback origin instead of an explicit callback URL. Local-only development should use demo mode; a real gateway callback needs an appropriate reachable HTTPS development endpoint.

Real checkout uses Paytm's Initiate Transaction API and CheckoutJS. Callback signatures are checked, then the signed Transaction Status API response is verified. Merchant ID, order ID, amount, transaction type, and transaction reference must match before the order is marked paid. Duplicate callbacks cannot create repeated success updates or downgrade an already paid order. An unverified callback never displays payment success.

Official references: [Initiate Transaction](https://www.paytmpayments.com/docs/api/initiate-transaction-api), [Verify Payment Status](https://www.paytmpayments.com/docs/jscheckout-verify-payment).

## Problems corrected from the previous payment flow

The previous request sent the literal value `MID`, used the old hard-coded staging gateway and localhost callback, accepted the browser's amount, and only logged the callback outcome. Its result template checked `RESPCODE == '01'` even after checksum verification failed. The new flow resolves runtime merchant configuration, separates demo/staging/production, calculates totals server-side, persists verified payment state, and shows success only through the verified result path.

Provider calls are mocked in the regression tests. The test suite uses a temporary in-memory database and dummy credentials, not your real accounts, orders, merchant credentials, or private configuration.
