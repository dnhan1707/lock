# Decisions

All decisions below are approved unless listed under "Open items". Product stories are in [user-stories.md](./user-stories.md), tasks in [plan.md](./plan.md), accounts in [external-tool-need.md](./external-tool-need.md).

## Provider and technical decisions

### ID and face verification provider. Options: Persona, Onfido, Stripe Identity, AWS Rekognition plus a document OCR. We must receive a stable document fingerprint and a liveness result. We never store raw ID images.
- **Recommendation: Stripe Identity.** Hosted capture flow (document + selfie + liveness), official React Native SDK (`@stripe/stripe-identity-react-native`, works with the `expo-dev-client` we already have), test mode with no paperwork, about $1.50 per verification. Our backend creates a VerificationSession and reads the result in a webhook, so we never touch images.
- Caveats: (1) Stripe returns no reusable face template, so **drop `face_hash` from the MVP schema**. Duplicate detection relies on the ID hash. (2) Document number and DOB are only returned if enabled and requested on the session, and may need extra API key permissions. Confirm in test mode first; if the document number is unavailable, hash `country + full name + date of birth` instead. Store `hash_version` so we can change this later.
- Runner-up: Persona (free sandbox, more configurable, more setup). Build behind a provider interface with a **fake provider** so Phase 1 works before any vendor account exists.

### Phone verification provider. Options: Twilio Verify, Firebase Auth.
- **Recommendation: Twilio Verify.** One REST call to send and one to check a code, no mobile SDK or native config, and it fits our own JWT backend. Firebase Auth would add a second identity system and native setup. Trial accounts can only text verified numbers, so in dev and tests use the magic login link workaround (see "Phase 1 workarounds" below) instead of an OTP.
### Hashing design. Use HMAC-SHA256 with a server-side pepper (kept in a secret manager, not in the DB) over the normalized country + document type + document number. Use a separate HMAC for the phone number (E.164). A face-template hash was considered and dropped (see the ID provider decision above). Plain unsalted hashes can be brute-forced because ID numbers have low entropy.
- **Recommendation: accept as written, with MVP simplifications.** Pepper comes from an env var (`HASH_PEPPER`, 32+ random bytes) now; move it to AWS Secrets Manager at deploy since we are already on AWS. Hash only ID and phone (no face hash, see above). Add a `hash_version` column. Never log raw values.
- Note: the 90-day wipe (below) deletes the hashes, which is exactly what lets a deleted user start over as a new user.
### Push provider. Expo Push (simplest) vs. FCM/APNs direct.
- **Recommendation: Expo Push.** `expo-notifications` on the app, one HTTPS call to Expo's push API from the backend (plain `httpx`, no SDK). Needs an EAS project ID, an FCM key for Android and an Apple Developer account for iOS. Push does not work in Expo Go, so use a dev build.
### Object storage. S3 or Cloudflare R2, with presigned uploads.
- **Decided: S3.** Implementation notes: private bucket, presigned PUT/GET URLs via `boto3`, size and MIME limits in the presign. Locally, run **MinIO** in docker compose and point `boto3` at it with `S3_ENDPOINT_URL`, so there are no AWS credentials in dev. Object keys are prefixed by `relationship_id` so archiving and wiping are simple.

### Redis hosting (local via Docker; managed in prod).
- **Recommendation:** `redis:7-alpine` in docker compose locally. In prod use **Upstash Redis** (free tier, TLS URL, no servers) or the Redis add-on of whichever host runs the API (Render or Railway). Use the `redis` Python package. Redis only holds disposable data (invites, breakup requests, rate limits), so losing it is safe.
### Auth/session model. Phone verification (OTP or login link, see Phase 1 workarounds), then short-lived JWT access token plus rotating refresh token.
- **Recommendation: accept as written.** `PyJWT` for a 15-minute access token. Refresh token is a random string, 30 days, stored hashed in Postgres and rotated on each use (reuse revokes the family). The app keeps both in `expo-secure-store`. Login must still succeed for users in the 90-day deletion cooldown, because logging in cancels the deletion.
### In-app purchase approach. StoreKit/Play Billing via RevenueCat or native, with server-side receipt validation.
- **Recommendation: RevenueCat** (`react-native-purchases`). It does receipt validation for both stores, so we skip the Apple and Google server APIs. Set the RevenueCat app user ID to our user UUID. The $19.99 fee is a consumable product. The backend confirms the purchase through RevenueCat's REST API or webhook, idempotent on transaction ID. Needs a dev build and store accounts, so **defer to Phase 5** and use a fake validator until then. Free until roughly $2.5k monthly revenue.

## Store policy and legal review

Concern: permanent account lock, no deletion, forced location tracking, and a public ledger conflict with Apple/Google account-deletion rules, privacy law (GDPR/CCPA) and consent rules.

**Approved answer:** free in-app deletion with a 90-day cooldown, mutual breakup, and the Divorce Fee. The written note (consent screens, jurisdiction limits, Divorce Fee flow) is still an open item at the bottom of this file.

The user stories for leaving the lock (mutual breakup, Divorce Fee) and account deletion (90-day cooldown) live in [user-stories.md](./user-stories.md), Epics 5 and 6.

### Impact of the store policy answer (approved)
- **Relationships are archived, not deleted.** Mutual breakup and the Divorce Fee both set `status='ended'`, `ended_at`, `ended_reason` (`mutual`, `divorce_fee`, `deletion_purge`). The "one active relationship per user" rule becomes a **partial unique index on active rows**, not a plain unique constraint. Ended relationships and their vault become the read-only "Past Matches" archive. Vault posts stay undeletable by users (still no DELETE route).
- **Breakup flow:** a request lives in Redis with a TTL, like invites. Accept before it expires and the lock ends instantly and for free. Divorce Fee ends the lock one-sided and pushes the partner.
- **Account deletion:** users get statuses `deactivating` (hidden from search and the ledger) and a `deletion_scheduled_for` timestamp (+90 days). Any login clears it. A daily purge job handles accounts past the date: it wipes the leaver's ID hash, phone hash, profile and authored vault posts, and ends the active relationship (`deletion_purge`). The relationship row stays archived, so the partner keeps their own posts in Past Matches. Per-table rules: [database.md](./database.md) (purge table). This replaces the old plan to hide the app icon and never delete, so the "cannot remove the home-screen icon" workaround is no longer needed.
- **Brutal push to the partner** is sent when deletion is requested.
- **Still true:** forced location and last-seen tags, plus the public ledger, remain legal and store risks. Keep the consent screens and the review.

### Phase 1 workarounds (decided while in development)
- **ID verification:** `dev_manual` provider. The user uploads an ID image (type and size checked, then discarded) and types the ID number and country. The typed number is hashed. Replaced by Stripe Identity before real users (plan section 6A).
- **Phone verification:** magic login link instead of an OTP. Stored in `login_links`; in dev the API returns and logs the link. Real delivery later: SMS containing the same link, or Twilio Verify.
- **Schema:** `users.verification_method` and nullable `users.phone_verified_at` mark dev-era accounts. The raw phone number is never stored.
- **Guard:** both workarounds refuse to run when `APP_ENV=production`.
- Schema details: [database.md](./database.md).

### Resolved questions (approved)
1. **Breakup window length:** 72 hours.
2. **Purge scope:** at day 90 the relationship ends, the leaver's data and authored posts are wiped, and the partner keeps their own posts in Past Matches.
3. **Lock during the 90 days:** the lock holds, and the partner is freed automatically at purge time.
4. **Ledger status during cooldown:** show the "Fled the App" placeholder while `deactivating`.
5. **Error code when an ID is already registered:** `ID_ALREADY_REGISTERED` when the existing account has no active lock. From Phase 3, `ALREADY_BOUND` (with the partner's public profile) when it does.
6. **Re-registration is a breach:** a locked user who tries to verify a new account with the same ID gets a `reregistration_attempt` breach event, and the partner gets a push.
7. **Breakup request ID:** there is at most one open request per relationship, so it is addressed by the relationship (Redis key `breakup:{relationship_id}`, routes under `/relationship/breakup-request`). No separate request ID.
8. **`bind_requests` audit rows:** a row is written for every invite and updated on cancel, decline, accept and expiry (see plan 2B and 2C).
9. **Ledger access and name search:** only signed-in, verified users can search. Name search returns only users who are locked or in the cooldown (`fled`). Free users return `not_found`, so the ledger cannot be used to look up people who are not locked.
10. **Purge retention:** `consents` (proof of what the user agreed to), `bind_requests`, `breach_events` and `certificates` are kept, because they hold only IDs and versions. The leaver's `login_links` rows are deleted so no `phone_hash` survives the purge.
11. **Legal and store-policy note due date:** before Phase 3, because Phase 3 ships the deletion flow and the punitive pushes.

## Open items

- Legal and store-policy note (record the mitigations). Due before Phase 3.
- Stripe Identity spike: does it return the document number? Record the result here.