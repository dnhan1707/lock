# External Tools and Accounts Needed

Source: [plan.md](./plan.md) and [decisions.md](./decisions.md). Tick the box when the account and keys are ready. Keep keys in `.env` only and never commit them.

## Needed in Phase 1 (identity)

Phase 1 needs **no external account** with the workarounds below. It runs in Expo Go.

| Done | Tool | Used for | MVP cost | Workaround for now | Notes |
| --- | --- | --- | --- | --- | --- |
| [ ] | **Stripe Identity** | ID, selfie and liveness check | Free in test mode, about $1.50 per real verification | `dev_manual` provider: user uploads an ID image and types the ID number and country. Image is checked for type and size, then discarded. The typed number is hashed. Auto-approved. | Going live requires Stripe approval. Spike first: does it return the document number? |
| [ ] | **Twilio Verify** | Phone verification | Free trial, then pay per SMS | Magic login link instead of an OTP. The link is returned by the API and logged in dev, and the app shows an "Open link" button. Table `login_links`. | Real delivery later: SMS containing the same link, or Twilio Verify. |
| [ ] | **Expo / EAS account** | Dev builds, push project ID, later store builds | Free tier | Expo Go for Phase 1 (image picker and deep links work there). | The EAS dev build is needed from Phase 3, because push and the Stripe SDK do not work in Expo Go. |

Both workarounds are blocked at startup when `APP_ENV=production`.

## Needed in Phase 3 (push)

| Done | Tool | Used for | Workaround for now | Notes |
| --- | --- | --- | --- | --- |
| [ ] | **Expo Push service** | Breach, breakup and deletion alerts | Fake push sender in tests and dev (logs the message). In-app red flag and breach list still work without push. | Free. Needs an EAS project ID. |
| [ ] | **Firebase project (FCM)** | Android push delivery | None needed until a real device test. | Free. Its key is added to Expo. |
| [ ] | **Apple Developer account** | iOS push and TestFlight | Android device or simulator first. | $99 per year. Also required for the Phase 5 in-app purchase. |

## Needed from Phase 1 (profile photo) and Phase 4 (vault)

| Done | Tool | Used for | Workaround for now | Notes |
| --- | --- | --- | --- | --- |
| [ ] | **AWS account with S3** | Profile photo, vault photos and voice notes | **MinIO in Docker** with the same `boto3` code (`S3_ENDPOINT_URL`). No AWS credentials in dev. | Create the real bucket before the first deployment. |

## Needed in Phase 5 (monetization)

| Done | Tool | Used for | Workaround for now | Notes |
| --- | --- | --- | --- | --- |
| [ ] | **RevenueCat** | Purchase validation for the $19.99 Divorce Fee | Fake purchase validator and a dev-only "simulate purchase" call. | Free at MVP volume. |
| [ ] | **App Store Connect** | iOS in-app product, store listing | None. Needed for any real sandbox purchase. | Uses the Apple Developer account. |
| [ ] | **Google Play Console** | Android in-app product, store listing | None. Needed for any real sandbox purchase. | $25 one-time. |

## Needed at deploy (not for local dev)

| Done | Tool | Used for | Workaround for now | Notes |
| --- | --- | --- | --- | --- |
| [ ] | **Upstash Redis** | Production Redis | Redis in Docker. | Free tier. |
| [ ] | **Backend host** (Render, Railway, Fly or AWS) | Runs the API and the daily purge job | `docker compose` locally. | Not chosen yet. |
| [ ] | **Managed Postgres** | Production database with backups | Postgres in Docker. | Often comes with the host. Not chosen yet. |
| [ ] | **AWS Secrets Manager** | Holds `HASH_PEPPER` in production | `HASH_PEPPER` in `.env`. | Uses the AWS account above. |
| [ ] | **Sentry** | Error tracking | Console logs. | Free tier. Optional. |
| [ ] | **GitHub Actions** | CI | Run tests locally. | Free. The repo is already on GitHub. |

## What can wait

- Everything above can wait, because fake providers and local Docker cover development.
- **For Phase 1 you need nothing external.** First needs: an Expo account and a dev build for Phase 3, Apple and Google accounts before Phase 5.
- Local Docker (Postgres, Redis, MinIO) needs no outside accounts.

## Before real users (swap-in checklist)

- [ ] Replace the `dev_manual` ID provider with Stripe Identity (and run the document-number spike).
- [ ] Replace the dev login link delivery with SMS (link) or Twilio Verify, and start setting `phone_verified_at`.
- [ ] Re-verify accounts with `verification_method = 'dev_manual'`.
- [ ] Confirm the production startup guard blocks the dev providers.

## Costs and approvals

- **Fixed costs:** Apple ($99 per year) and Google ($25 once).
- **Longest lead time:** Stripe live-mode approval and store review. Start the Stripe application early because it can take days.
- **Legal:** a lawyer review is also an external dependency. The plan flags the public ledger and forced location tracking as the highest-risk items.
