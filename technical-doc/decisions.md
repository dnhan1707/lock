Decisions needed before coding (blockers)
[ ] ID and face verification provider. Options: Persona, Onfido, Stripe Identity, AWS Rekognition plus a document OCR. We must receive a stable document fingerprint and a liveness result. We never store raw ID images.
- **Recommendation: Stripe Identity.** Hosted capture flow (document + selfie + liveness), official React Native SDK (`@stripe/stripe-identity-react-native`, works with the `expo-dev-client` we already have), test mode with no paperwork, about $1.50 per verification. Our backend creates a VerificationSession and reads the result in a webhook, so we never touch images.
- Caveats: (1) Stripe returns no reusable face template, so **drop `face_hash` from the MVP schema**. Duplicate detection relies on the ID hash. (2) Document number and DOB are only returned if enabled and requested on the session, and may need extra API key permissions. Confirm in test mode first; if the document number is unavailable, hash `country + full name + date of birth` instead. Store `hash_version` so we can change this later.
- Runner-up: Persona (free sandbox, more configurable, more setup). Build behind a provider interface with a **fake provider** so Phase 1 works before any vendor account exists.
[ ] Phone verification provider. Options: Twilio Verify, Firebase Auth.
- **Recommendation: Twilio Verify.** One REST call to send and one to check a code, no mobile SDK or native config, and it fits our own JWT backend. Firebase Auth would add a second identity system and native setup. Trial accounts can only text verified numbers, so use the fake provider (fixed code `000000`) in dev and tests.
[ ] Hashing design. Use HMAC-SHA256 with a server-side pepper (kept in a secret manager, not in the DB) over the normalized country + document type + document number. Use a separate HMAC for the phone number (E.164) and for the face template or provider face ID. Plain unsalted hashes can be brute-forced because ID numbers have low entropy.
- **Recommendation: accept as written, with MVP simplifications.** Pepper comes from an env var (`HASH_PEPPER`, 32+ random bytes) now; move it to AWS Secrets Manager at deploy since we are already on AWS. Hash only ID and phone (no face hash, see above). Add a `hash_version` column. Never log raw values.
- Note: the 90-day wipe (below) deletes the hashes, which is exactly what lets a deleted user start over as a new user.
[ ] Push provider. Expo Push (simplest) vs. FCM/APNs direct.
- **Recommendation: Expo Push.** `expo-notifications` on the app, one HTTPS call to Expo's push API from the backend (plain `httpx`, no SDK). Needs an EAS project ID, an FCM key for Android and an Apple Developer account for iOS. Push does not work in Expo Go, so use a dev build.
[ ] Object storage. S3 or Cloudflare R2, with presigned uploads.
- Use S3
- **Decided: S3.** Implementation notes: private bucket, presigned PUT/GET URLs via `boto3`, size and MIME limits in the presign. Locally, run **MinIO** in docker compose and point `boto3` at it with `S3_ENDPOINT_URL`, so there are no AWS credentials in dev. Object keys are prefixed by `relationship_id` so archiving and wiping are simple.

[ ] Redis hosting (local via Docker; managed in prod).
- **Recommendation:** `redis:7-alpine` in docker compose locally. In prod use **Upstash Redis** (free tier, TLS URL, no servers) or the Redis add-on of whichever host runs the API (Render or Railway). Use the `redis` Python package. Redis only holds disposable data (invites, breakup requests, rate limits), so losing it is safe.
[ ] Auth/session model. Phone OTP, then short-lived JWT access token plus rotating refresh token.
- **Recommendation: accept as written.** `PyJWT` for a 15-minute access token. Refresh token is a random string, 30 days, stored hashed in Postgres and rotated on each use (reuse revokes the family). The app keeps both in `expo-secure-store`. Login must still succeed for users in the 90-day deletion cooldown, because logging in cancels the deletion.
[ ] In-app purchase approach. StoreKit/Play Billing via RevenueCat or native, with server-side receipt validation.
- **Recommendation: RevenueCat** (`react-native-purchases`). It does receipt validation for both stores, so we skip the Apple and Google server APIs. Set the RevenueCat app user ID to our user UUID. The $19.99 fee is a consumable product. The backend confirms the purchase through RevenueCat's REST API or webhook, idempotent on transaction ID. Needs a dev build and store accounts, so **defer to Phase 5** and use a fake validator until then. Free until roughly $2.5k monthly revenue.

[ ] Store policy and legal review. Permanent account lock, no deletion, forced location tracking, and a public ledger conflict with Apple/Google account-deletion rules, privacy law (GDPR/CCPA) and consent rules. Record the decision and the mitigations (explicit consent screens, jurisdiction limits, divorce fee flow) in a short doc before Phase 3.
- Epic 1: The "Break Up" Flow (Keep the account, ditch the partner)
As a locked user, I want to click a "Mutual Breakup" button, so that I can initiate a free unlock request to my partner.

As a partner receiving a mutual breakup request, I want a limited time window to agree, so that we can sever the lock instantly and for free.

As a mutually broken-up user, I want my shared timeline moved to a private "Past Matches" archive, so that my active profile is instantly cleared and ready for a new "Forever Bind" request.

As a locked user who wants out immediately, I want the option to pay a $19.99 "Divorce Fee" via in-app purchase, so that I can instantly force a one-sided breakup without my partner's consent.

As the partner of someone who paid the Divorce Fee, I want to receive an immediate, dramatic push notification that my partner bought their way out of the relationship, so that I know our lock has been severed.

- Epic 2: Account Deletion & The 90-Day Trap (Privacy Compliance)
As any user, I want to find a free "Delete Account" button in my privacy settings, so that the app complies with international privacy laws (GDPR/CCPA).

As a user requesting account deletion, I want to be placed into a mandatory 90-day deactivation cooldown, so that my account is hidden but my data is not immediately wiped.

As a locked partner of someone deleting their account, I want to receive a brutal notification saying "Your partner has initiated account deletion to escape the lock," so that their attempt to flee the app is exposed.

As a user in the 90-day cooldown, I want the ability to simply log back into the app to cancel the deletion process, so that my account and relationship lock are instantly restored to normal.

As a user who waits out the full 90 days, I want my ID hash, phone number, and relationship history permanently wiped from the database, so that my legal right to be forgotten is honored and I can eventually start over as a brand new user.

### Impact of the store policy answer (my analysis, needs your OK)
- **Relationships are archived, not deleted.** Mutual breakup and the Divorce Fee both set `status='ended'`, `ended_at`, `ended_reason` (`mutual`, `divorce_fee`, `deletion_purge`). The "one active relationship per user" rule becomes a **partial unique index on active rows**, not a plain unique constraint. Ended relationships and their vault become the read-only "Past Matches" archive. Vault posts stay undeletable by users (still no DELETE route).
- **Breakup flow:** a request lives in Redis with a TTL, like invites. Accept before it expires and the lock ends instantly and for free. Divorce Fee ends the lock one-sided and pushes the partner.
- **Account deletion:** users get statuses `deactivating` (hidden from search and the ledger) and a `deletion_scheduled_for` timestamp (+90 days). Any login clears it. A daily purge job wipes ID hash, phone, and relationship history for accounts past the date. This replaces the old plan to hide the app icon and never delete, so the "cannot remove the home-screen icon" workaround is no longer needed.
- **Brutal push to the partner** is sent when deletion is requested.
- **Still true:** forced location and last-seen tags, plus the public ledger, remain legal and store risks. Keep the consent screens and the review.

### Phase 1 workarounds (decided while in development)
- **ID verification:** `dev_manual` provider. The user uploads an ID image (type and size checked, then discarded) and types the ID number and country. The typed number is hashed. Replaced by Stripe Identity before real users (plan section 6A).
- **Phone verification:** magic login link instead of an OTP. Stored in `login_links`; in dev the API returns and logs the link. Real delivery later: SMS containing the same link, or Twilio Verify.
- **Schema:** `users.verification_method` and nullable `users.phone_verified_at` mark dev-era accounts. The raw phone number is never stored.
- **Guard:** both workarounds refuse to run when `APP_ENV=production`.
- Schema details: [database.md](./database.md).

### Resolved questions (approved: suggestions adopted)
1. **Breakup window length.** I suggest 72 hours.
2. **Purge scope.** When a user's data is wiped at day 90, does the partner lose the shared archive too? I suggest: the relationship ends, the leaver's data and authored posts are wiped, and the partner keeps their own posts in Past Matches.
3. **Does the lock hold during the 90 days?** Your stories say yes (partner stays locked until day 90). Confirm that the partner is freed automatically at purge time.
4. **Ledger status during cooldown.** Show the "Fled the App" placeholder while deactivating?

[ ] Record each decision in api.md or database.md (or a new decisions.md).