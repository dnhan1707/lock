# Project Lock: Build Plan

Source docs: [user-stories.md](./user-stories.md), [building-phase.md](./building-phase.md), [api.md](./api.md), [database.md](./database.md), [backend README](../project-lock-backend/README.md).

How to use: tick `[x]` when done. Each phase ends with a **Phase exit gate**. Do not start the next phase until the gate is green.

## 0. Current state (baseline)

| Area | State |
| --- | --- |
| Backend (`project-lock-backend`) | FastAPI + async SQLAlchemy + Postgres 17 + Alembic in Docker. Only `GET /health` exists. No models, no migrations, no Redis, no auth, no tests. Seeder framework exists (`seeds/`). |
| Frontend (`project-lock`) | Fresh Expo SDK 58 / React Native 0.88 / expo-router template. Only template screens (`index.tsx`, `explore.tsx`, tabs). No API client, state, auth, or tests. |
| Docs | `api.md` and `database.md` are empty stubs. [decisions.md](./decisions.md) holds the approved choices. |

## 1. Decisions at a glance

Details live inside the phase that uses them. Full reasoning: [decisions.md](./decisions.md). Accounts and workarounds: [external-tool-need.md](./external-tool-need.md). Schema: [database.md](./database.md).

| Topic | Final choice | Workaround now (development) | Lands in |
| --- | --- | --- | --- |
| ID verification | Stripe Identity | `dev_manual`: upload image (discarded) + typed ID number and country | Real: section 6A |
| Phone verification | SMS link or Twilio Verify | Magic login link (`login_links`), returned by the API in dev | Real: section 6A |
| Hashing | HMAC-SHA256 + pepper, ID and phone only, `hash_version` | Pepper in `.env` | Phase 1 |
| Auth | JWT (15 min) + rotating refresh token (30 days), `PyJWT` | none | Phase 1 |
| Object storage | S3 | MinIO in Docker | Phase 1 (profile photo), Phase 4 |
| Redis | Upstash in prod | Docker | Phase 1 (rate limits), Phase 2 |
| Push | Expo Push | Fake sender | Phase 3 |
| Lock exits | Mutual breakup (free), account deletion (90-day cooldown), Divorce Fee ($19.99) | none | Phase 3, 3, 5 |
| In-app purchase | RevenueCat | Fake validator | Phase 5 |

Policy decisions (adopted): breakup window **72 hours**; at day 90 the leaver's data and authored posts are wiped and the partner keeps their own posts in Past Matches; the lock holds during the 90 days and the partner is freed at purge; the ledger shows "Fled the App" during the cooldown; relationships are archived, never deleted by users.

Checklist:
- [x] Decisions recorded in [decisions.md](./decisions.md).
- [x] Phase 1 workarounds decided (no Stripe or Twilio yet).
- [ ] Short legal and store-policy note (see section 6B). Finish it before Phase 4.
- [ ] Keep [api.md](./api.md) and [database.md](./database.md) updated as each phase lands.

## 2. Cross-cutting setup (do once, early)

Only tooling that every phase shares. Phase-specific setup lives in each phase.

### Backend tooling
- [ ] Add `pytest`, `pytest-asyncio`, `httpx` (ASGI test client), `ruff`, `mypy` to the pinned `requirements.txt` (dev section or `requirements-dev.txt`).
- [ ] Test config: a separate `lock_test` Postgres DB (compose service or profile). Fixtures create the schema via Alembic and roll back or truncate per test.
- [ ] Add a `tests/` layout: `tests/unit`, `tests/api`, `tests/db`, `tests/concurrency`.
- [ ] Settings: `APP_ENV`, `PROVIDERS` (`fake` or `real`, `fake` by default locally and in CI). Startup guard: dev providers and dev-only behavior are refused when `APP_ENV=production`.
- [ ] Standard error envelope (`{code, message, details}`) and stable error codes (for example `ALREADY_BOUND`, `ID_ALREADY_REGISTERED`).
- [ ] Structured logging plus request IDs.
- [ ] Verification: `docker compose run --rm api pytest` passes on an empty suite plus a `/health` test.

### Frontend tooling
- [ ] Add testing: `jest-expo`, `@testing-library/react-native`, and `msw` (or a fetch mock) for the API.
- [ ] Add `npm run typecheck` (`tsc --noEmit`) and `npm test` scripts alongside the existing `expo lint`.
- [ ] Add API client layer (`src/api/`), typed with types generated from the FastAPI OpenAPI schema (for example `openapi-typescript`).
- [ ] Add server-state and secure storage: TanStack Query, `expo-secure-store` for tokens.
- [ ] Add env config: `EXPO_PUBLIC_API_URL` (document the Android emulator `10.0.2.2` and real-device LAN IP cases).
- [ ] Replace template screens with the real route groups: `(auth)`, `(onboarding)`, `(app)`. Remove the Expo welcome content in `src/app/index.tsx`.
- [ ] Shared UI kit: themed `Button`, `Input`, `Screen`, `WarningScreen`, using the existing `src/constants/theme.ts`.
- [ ] Verification: `npm run typecheck`, `npm run lint`, `npm test` pass; app boots on iOS sim, Android emulator, and web.

### CI
- [ ] GitHub Actions: backend (ruff, mypy, pytest with Postgres and Redis services) and frontend (typecheck, lint, jest) on every PR.

### Docs
- [ ] Fill [api.md](./api.md) (endpoint table, request and response shapes, error codes) as endpoints land.
- [ ] Fill [database.md](./database.md) (tables, constraints, ER diagram) as migrations land.

---

## Phase 1: Core Infrastructure & Identity

Goal: an irreversible identity layer exists before any pairing.

**Phase 1 runs with no external accounts.** Decisions applied: HMAC hashing for ID and phone, JWT plus rotating refresh tokens, MinIO for the profile photo, Redis for rate limits. Workarounds: `dev_manual` ID provider (upload, typed number) and magic login links instead of OTP. Both are blocked in production. See [external-tool-need.md](./external-tool-need.md).

### 1.0 Phase 1 setup
- [ ] `docker-compose.yml`: add `redis` (`redis:7-alpine`) and `minio` services. Add `REDIS_URL`, `S3_ENDPOINT_URL`, `S3_BUCKET`, `HASH_PEPPER`, `JWT_SECRET`, `APP_BASE_URL`, and `LINK_DELIVERY=dev` to `.env.example` and `app/core/config.py`.
- [ ] Pin backend dependencies: `redis`, `PyJWT`, `boto3`, `phonenumbers`, `python-multipart`, plus `fakeredis` for tests.
- [ ] Provider interfaces with dev implementations: `IdentityProvider` (`dev_manual`), `LinkSender` (`dev`: returns and logs the link), `ObjectStorage` (MinIO via `boto3`).
- [ ] Frontend (runs in Expo Go): `expo-image-picker`, `expo-linking` (already installed), `expo-secure-store`. No native build needed yet.

### 1A. Database schema (backend)
Full column list, constraints, and triggers: [database.md](./database.md) (Phase 1 tables).
- [ ] Tables: `users`, `login_links`, `identity_verifications`, `refresh_tokens`, `consents`.
- [ ] `users` carries `status` (`pending_verification`, `verified`, `deactivating`, `purged`), `verification_method` (`dev_manual` / `stripe`), nullable `phone_verified_at`, `deletion_scheduled_for`, `hash_version`. "Locked" is derived from an active relationship (Phase 2), never stored on the user.
- [ ] `id_hash` and `phone_hash` are unique and nullable (null before verification and after purge). A DB trigger makes them immutable once set. The only exception is the Phase 3 purge, which sets `app.allow_purge`. No face hash.
- [ ] Alembic migration generated and reviewed. Model modules imported in `app/db/models/__init__.py`.
- [ ] Seeder for sample users (idempotent, registered in `SEEDERS`, refused in production).
- [ ] **Tests (db):**
  - [ ] Inserting a second user with the same `id_hash` or `phone_hash` raises `IntegrityError`.
  - [ ] Handle uniqueness is case-insensitive.
  - [ ] Updating a hash column is rejected by the trigger (except through the purge path, tested in Phase 3).
  - [ ] `alembic upgrade head`, then `downgrade base`, then `upgrade head` works on an empty DB.
  - [ ] Seeder runs twice with no duplicate rows.
  - [ ] A `login_links` row cannot be inserted with a duplicate `token_hash`.

### 1B. Identity hashing (backend)
- [ ] `app/core/security/hashing.py`: normalization functions (ID number, country, phone to E.164 with `phonenumbers`, name casing) and the HMAC-SHA256 hasher with the pepper from settings. Output is tagged with `hash_version`.
- [ ] Pepper comes from `HASH_PEPPER` (32+ random bytes); startup fails if it is missing in production.
- [ ] **Tests (unit):**
  - [ ] Same input in different formats (spaces, dashes, case) gives the same hash.
  - [ ] Different pepper gives a different hash.
  - [ ] Phone numbers `+1 (415) 555-0100` and `4155550100` (with region US) normalize identically.
  - [ ] Known-answer test vectors are pinned so an accidental algorithm change fails CI.
  - [ ] Raw values never appear in logs (log capture assertion).

### 1C. Login link, identity, and profile API (backend)
- [ ] `POST /auth/link/start` `{phone, region}`: normalize and hash the phone, rate limit (Redis, per phone and per IP), create a `login_links` row with a 15-minute single-use token (only its hash is stored), and hand the link `projectlock://auth/verify?token=...` (or the `APP_BASE_URL` web equivalent) to the `LinkSender`. In dev the response includes the link and it is logged. The raw phone is never stored or logged.
- [ ] `POST /auth/link/verify` `{token}`: in one transaction, check the token is unexpired and unconsumed, mark it consumed, create the user from `phone_hash` if new (status `pending_verification`) or find the existing one, and issue tokens. A user in the deletion cooldown who logs in has the deletion cancelled (Phase 3C).
- [ ] `POST /verification/manual` (multipart: image, `document_number`, `country`): check image type and size, **discard the image**, hash the typed number, and reject with `ID_ALREADY_REGISTERED` if the `id_hash` exists. On success set `verified`, `verification_method='dev_manual'`, and write an `identity_verifications` row. This route is refused when `APP_ENV=production`.
- [ ] `POST /consents`: record accepted consent types and versions.
- [ ] `POST /users/me/profile`: set handle, display name, and an optional photo (presigned upload to MinIO). Allowed only after verification.
- [ ] `GET /users/me`.
- [ ] `POST /auth/refresh`, `POST /auth/logout`.
- [ ] Auth dependency (`get_current_user`) and a `require_verified` dependency.
- [ ] **Tests (api):**
  - [ ] Link happy path: start, then verify, then tokens issued and a user exists.
  - [ ] Link rejected when expired, already used, unknown, or tampered. Rapid repeated starts return 429 with `Retry-After`.
  - [ ] Starting a link twice for the same phone yields one user. Same phone in different formats maps to the same user.
  - [ ] Manual ID: same ID number from a different phone gets `ID_ALREADY_REGISTERED`; same number in a different format is also rejected; the image is not persisted anywhere.
  - [ ] Production guard: with `APP_ENV=production`, the app refuses to start with dev providers, and `/verification/manual` and the dev link response are unavailable.
  - [ ] Profile endpoint refuses unverified users (403) and duplicate handles (409, case-insensitive).
  - [ ] Expired or invalid JWT gets 401. Refresh token rotation: reuse of an old refresh token revokes the family.
  - [ ] Response bodies and logs never include a hash, raw phone, or document number.

### 1D. Basic onboarding UI (frontend, Expo Go)
- [ ] Screens: Welcome, Phone entry ("Send me a link"), Link sent (dev: "Open link" button and paste field), Consent, ID upload (pick or take a photo, type ID number and country), Verification result, Create profile (handle, name, photo), Done.
- [ ] Deep link handling: `projectlock://auth/verify?token=...` (through `expo-linking`; the scheme is set in `app.json`) calls `/auth/link/verify`. Handle invalid and expired links with a "request a new link" state.
- [ ] Auth store plus secure token storage. Auth-gated routing: unauthenticated goes to `(auth)`, unverified or no handle goes to `(onboarding)`, otherwise `(app)`.
- [ ] Clear, explicit consent screen describing the permanent identity binding, the shared location, and the public ledger. Consent is sent to `/consents`.
- [ ] The ID upload screen is a dev screen. It is replaced by the Stripe Identity sheet in section 6A, so keep it behind a small `IdentityStep` component.
- [ ] **Tests (frontend):**
  - [ ] Component: phone validation, link states, handle error display, ID form validation.
  - [ ] Hook and unit: auth store, token refresh on 401, router guard redirects for each user status, deep link parsing.
  - [ ] Integration (RNTL and mocked API): full onboarding flow reaches the home screen; `ID_ALREADY_REGISTERED` shows the correct error screen; expired link shows the retry state; photo permission denied shows a recovery state.
  - [ ] Manual device pass in Expo Go on iOS and Android: open the link, upload an ID photo, kill and relaunch the app mid-onboarding and resume at the right step.

### Phase 1 exit gate
- [ ] All Phase 1 tests are green in CI.
- [ ] Manual E2E on a device with no external accounts: new user reaches a verified profile through the link and the manual ID step.
- [ ] Attempting to register a second account with the same ID or phone is blocked at both the API and DB level.
- [ ] The production guard test is green.
- [ ] `api.md` and `database.md` are updated.

---

## Phase 2: The Permanent Lock (Mutual Consent)

Goal: bulletproof pairing with no race conditions.

**Decisions applied:** relationships are archived, not deleted; invites live in Redis (Docker locally, Upstash in prod, already added in Phase 1); no external accounts needed.

### 2A. Schema
Full definitions: [database.md](./database.md) (Phase 2 tables).
- [ ] Tables: `relationships` (`status` `active` / `ended`, `ended_reason`, `ended_by_user_id`), `relationship_members`, `certificates`, `bind_requests`.
- [ ] `CHECK (user_a_id < user_b_id)`, plus `relationship_members` with a partial unique index on `user_id WHERE active`, because a user can be `a` in one row and `b` in another. Ended rows can repeat, so users can bind again later and keep a history.
- [ ] **Tests (db):**
  - [ ] A user cannot be in two active relationships, including the case where they are `a` in one and `b` in another.
  - [ ] After a relationship is set to `ended`, the same user can be in a new active one, and the old row is still present.
  - [ ] Self-pairing is rejected.
  - [ ] `(a, b)` and `(b, a)` cannot both be active.

### 2B. Invite system (Redis)
- [ ] `POST /binds` (by partner handle): create an invite with a TTL (for example 24h), one pending outgoing invite per sender.
- [ ] `GET /binds/incoming`, `GET /binds/outgoing`.
- [ ] `POST /binds/{id}/cancel` (sender), `POST /binds/{id}/decline` (receiver).
- [ ] Rate limiting (Redis counters): per-user and per-IP limits on creating invites and on handle lookups (prevents handle enumeration).
- [ ] Guards: sender and receiver must both be `verified`, have no active relationship, and not be in the deletion cooldown. Cannot bind to self.
- [ ] **Tests:**
  - [ ] Unit (fakeredis): TTL expiry, one pending invite per sender, rate-limit counters reset on window.
  - [ ] API: unknown handle, self handle, locked target (hand-off to Phase 3 behavior), expired invite, double accept.
  - [ ] Rate limiting returns 429 with `Retry-After`.

### 2C. The transaction (accept and lock)
- [ ] `POST /binds/{id}/accept` requires a **warning-flow completion token** (see 2D) so it cannot be accepted without going through all steps.
- [ ] One DB transaction: lock both user rows in a fixed order (`SELECT ... FOR UPDATE`), re-check neither has an active relationship, insert `relationships`, `relationship_members` and `certificates`, delete the invite from Redis, and commit.
- [ ] Idempotent: repeated accept returns the same result.
- [ ] `GET /relationship` and `GET /certificate` (and a shareable PDF or image render later).
- [ ] **Tests (concurrency, most critical):**
  - [ ] Two accepts for the same invite at once: exactly one relationship.
  - [ ] User A invites B and C; B and C accept at the same time: exactly one succeeds, the other gets `ALREADY_BOUND`.
  - [ ] A accepts from B while B accepts from C (cross-pairing): no deadlock, consistent final state.
  - [ ] 50 parallel random pair attempts across 20 users: every user is in at most one relationship and the DB constraints hold.
  - [ ] Failure mid-transaction (inject an error after the relationship insert) leaves no partial state.
  - [ ] Certificate serial is unique and the payload hash verifies.

### 2D. Warning flow (frontend)
- [ ] Send bind UI: search by handle, confirm, pending state, cancel.
- [ ] Incoming invite screen and push or in-app badge.
- [ ] Multi-screen "Point of No Return" flow (for example 5 screens). Each screen needs a deliberate action (hold-to-confirm, typed phrase on the last screen). Back-navigation restarts the flow. The completion token is requested from the server only after the last step.
- [ ] Success screen showing the minted Marriage Certificate (animated), plus the locked home state.
- [ ] **Tests (frontend):**
  - [ ] Component: each warning screen blocks "Next" until its action is complete; the typed phrase must match exactly.
  - [ ] Navigation: leaving mid-flow resets progress; the accept call is never fired before the last step.
  - [ ] Integration: send, receive, accept shows the certificate; race error (`ALREADY_BOUND`) shows the correct screen; expired invite state.
  - [ ] Manual: two devices or simulators complete a lock end to end.

### Phase 2 exit gate
- [ ] Concurrency suite green and repeated 100 times without a flake.
- [ ] Two real devices can lock and both see the certificate.
- [ ] Redis outage test: invite creation fails safely (503) and existing locks are unaffected.
- [ ] Push for incoming invites is optional here. Push infrastructure lands in Phase 3B.

---

## Phase 3: The "Rage-Bait" Defenses

**Decisions applied:** Expo Push (fake sender until a real device test), 90-day deletion cooldown with a daily purge job, free mutual breakup with a 72-hour window, relationships archived into Past Matches. Needs the **EAS dev build** from this phase (push does not work in Expo Go). See [external-tool-need.md](./external-tool-need.md).

### 3.0 Phase 3 setup
- [ ] Backend: pin `httpx` usage for the Expo Push API. Create the `PushSender` interface with a fake sender (logs the message) and an Expo implementation.
- [ ] Backend: scheduled-job entry point `python -m app.jobs.purge` (run daily; in prod from a cron or scheduler service). No Celery for the MVP.
- [ ] Frontend: install `expo-notifications` and create the first **EAS dev build** (`expo-dev-client` is already installed) for iOS and Android. Needs the Expo project ID, FCM key (Android), and Apple Developer account (iOS). Until then the fake sender plus the in-app red flag cover testing.

### 3A. Rejection engine
- [ ] Central check `assert_can_bind(user)`, used by: bind creation and bind accept. It fails with `ALREADY_BOUND` if the user has an active relationship.
- [ ] Re-registration with the same ID or phone hash as a user who is in an active lock returns `ALREADY_BOUND`, even if they try a fresh account (the hash unique constraint plus the lookup of the existing account's relationship).
- [ ] Error payload for the *new partner*: original partner's public profile (handle, display name, photo) and `locked_at`. Define exactly which fields are exposed.
- [ ] **Tests:**
  - [ ] Locked user sends a bind: `ALREADY_BOUND`.
  - [ ] Someone invites a locked user: response includes the bound partner's profile.
  - [ ] Locked user re-onboards with a new phone but the same ID: blocked and mapped back to the original account.
  - [ ] After the relationship ended (breakup, divorce), the same user can bind again.
  - [ ] Response never leaks hashes or private data (field allowlist test).

### 3B. Snitch notifications
- [ ] Tables `device_tokens` (`POST /devices` to register Expo push tokens) and `breach_events` (see [database.md](./database.md)). `breach_events` rows are append-only (trigger rejects UPDATE and DELETE; no such endpoints).
- [ ] Push sender interface: Expo Push API over `httpx`, fake sender for tests. Run sends from FastAPI background tasks with retries.
- [ ] `breach_events` table: `relationship_id`, `offender_user_id`, `type` (`new_bind_attempt`, `deletion_requested`), `created_at`. Append-only (no UPDATE or DELETE endpoints).
- [ ] On a rejected attempt, write a breach event and push to the original partner.
- [ ] `GET /relationship/breaches` for the shared dashboard "red flag".
- [ ] **Tests:**
  - [ ] Backend: a breach event is created exactly once per attempt; push sender is called with the partner's tokens (fake sender); failed push is retried and does not fail the request.
  - [ ] Backend: tokens that Expo reports as invalid (`DeviceNotRegistered`) are pruned.
  - [ ] Frontend: notification permission flow, tap on notification deep-links to the dashboard; red flag appears and cannot be dismissed.
  - [ ] Manual: real push on a physical device (iOS and Android) through the dev build.

### 3C. Account deletion with the 90-day cooldown
- [ ] `POST /users/me/deletion`: sets `status='deactivating'`, `deletion_scheduled_for = now + 90 days`, revokes refresh tokens, writes a `deletion_requested` breach event, and sends the "Your partner has initiated account deletion to escape the lock" push. The relationship **stays active**.
- [ ] Any successful login (`/auth/link/verify`) clears `deletion_scheduled_for` and restores `verified`. The lock is unaffected.
- [ ] Users in `deactivating` are hidden from handle search and invites. The Phase 5 ledger shows them as "Fled the App".
- [ ] Daily purge job (`python -m app.jobs.purge`) for accounts past `deletion_scheduled_for`, in one transaction per user (it sets `app.allow_purge`): end the active relationship with `ended_reason='deletion_purge'` (partner is freed), wipe `id_hash`, `phone_hash`, handle, name, photo, and delete refresh tokens, device tokens, consents and identity verifications, keeping the `users` row as a tombstone (`status='purged'`). Per-table rules are in [database.md](./database.md) (purge table). Phase 4 extends the job to delete the leaver's vault posts, S3 objects and presence. The partner keeps their own posts in Past Matches. This is the only code path allowed to touch the immutable hash columns.
- [ ] Frontend: free "Delete Account" button in privacy settings with a clear 90-day explanation. After confirming, the app signs out and shows a "deletion scheduled, log in to cancel" screen. Logging back in shows a "deletion cancelled" confirmation.
- [ ] **Tests:**
  - [ ] API: request deletion sets the status and date, revokes tokens, and keeps the relationship active; partner gets the push and a breach event.
  - [ ] Login during the cooldown cancels the deletion and restores access.
  - [ ] Purge job (with time frozen or the date mocked): not-yet-due accounts are untouched; due accounts have hashes, handle and profile wiped, relationship ended with `deletion_purge`; running it twice is safe. (Vault posts and S3 objects are added to this test in Phase 4.)
  - [ ] After purge, the same person can register as a new user with the same ID and phone.
  - [ ] Route-table scan test: no route deletes `relationships` or `vault_posts`. Only the purge job (and the Phase 5 retention rules) may.
  - [ ] Frontend: delete flow signs out and shows the scheduled screen; re-login shows the cancelled state.

### 3D. Mutual breakup and Past Matches (free exit)
- [ ] `POST /relationship/breakup-requests`: stores a request in Redis with a **72-hour TTL**, one open request per relationship, and pushes the partner.
- [ ] `POST /relationship/breakup-requests/{id}/accept` (partner only) ends the lock instantly: in one transaction set the relationship `ended` (`ended_reason='mutual'`), flip `relationship_members.active` to false, and notify both users. `.../decline` and `.../cancel` also exist. Expired requests do nothing.
- [ ] `GET /past-matches` and `GET /past-matches/{relationship_id}`: read-only archive of ended relationships with their vault and certificate. Only the two former partners can read it. New posts are rejected on ended relationships.
- [ ] Frontend: "Mutual Breakup" button, pending and incoming states with a countdown, the archive screen, and the home screen resetting to "ready to bind" after the break.
- [ ] **Tests:**
  - [ ] API: only a member can request; the partner can accept; the requester cannot accept their own request; expired request returns `BREAKUP_EXPIRED`.
  - [ ] After acceptance, both users can bind again, the old timeline appears in Past Matches, and posting to it fails.
  - [ ] Concurrency: accepting a breakup while one party accepts a new bind, and double accept, leave consistent state.
  - [ ] Frontend: countdown and states, archive is read-only with no delete control.

### Phase 3 exit gate
- [ ] A breach attempt on device 1 produces a push and a red flag on device 2 within a few seconds.
- [ ] Requesting account deletion on device 1 pushes device 2; logging back in cancels it.
- [ ] Mutual breakup works end to end and frees both users to bind again.
- [ ] Purge job tested against a database copy with due and not-due accounts.
- [ ] Route-table scan test is green in CI.

---

## Phase 4: The Shared Vault & Transparency

**Decisions applied:** S3 for media (MinIO already running from Phase 1, so no new service), append-only vault, presence has no off switch, purge job extended to wipe the leaver's data. The real S3 bucket is only needed at deployment.

### 4A. Vault (storage and timeline)
- [ ] Table `vault_posts` (see [database.md](./database.md)), append-only for users.
- [ ] Private bucket, keys prefixed by `relationship_id`. Presigned PUT URLs with `boto3` (`POST /vault/uploads`) with size and MIME limits, and presigned GET URLs for reads. Reuse the Phase 1 `ObjectStorage` interface.
- [ ] Extend the Phase 3C purge job: delete the leaver's `vault_posts`, their S3 objects, and their `presence` row.
- [ ] `POST /vault/posts` (active relationship only), `GET /vault/posts` (cursor pagination, newest first, signed read URLs).
- [ ] Only the two partners can read or write. **No PUT, PATCH, or DELETE routes exist.** Ended relationships are read-only through Past Matches (Phase 3D).
- [ ] DB-level protection: trigger or revoked privileges so rows cannot be updated or deleted by the app role. The only exception is the Phase 3C purge job, which uses a dedicated role or function.
- [ ] **Tests:**
  - [ ] API: post and read as a partner; a non-partner gets 403/404; a user without an active relationship gets 403 on posting.
  - [ ] Posting to an ended relationship is rejected.
  - [ ] Upload limits: oversized or wrong MIME is rejected.
  - [ ] Route-table scan: no DELETE, PUT, or PATCH under `/vault`.
  - [ ] DB: direct UPDATE or DELETE on `vault_posts` as the app role fails; the purge path works and deletes only the leaver's posts and S3 objects while the partner's posts remain.
  - [ ] Pagination is stable with equal timestamps.

### 4B. Vault UI
- [ ] Timeline screen, composer (photo via `expo-image-picker`, voice via `expo-audio`, text promise), upload progress and retry.
- [ ] No delete or edit controls anywhere. Copy explains permanence before posting.
- [ ] **Tests (frontend):**
  - [ ] Component: post item has no delete control; composer states (uploading, failed, retry).
  - [ ] Integration: create each post type and see it in the timeline; offline and failed upload handling.
  - [ ] Manual: recording permissions, large photos, playback.

### 4C. Forced tracking (Last Seen and Location)
- [ ] Table `presence` (see [database.md](./database.md)): latest value only, no history, no sharing-off column.
- [ ] `PUT /presence` heartbeat (foreground, plus background location with `expo-location` and `expo-task-manager`). `GET /relationship/partner-presence` (active relationships only; the purge wipes the leaver's presence).
- [ ] No privacy-toggle field exists in the schema or API. The settings screen shows the tags as locked and non-interactive.
- [ ] Define and document retention (latest value only vs. history) and the permission-denied behavior (for example, show "Location unavailable" to the partner, which is itself visible).
- [ ] **Tests:**
  - [ ] API: heartbeat updates `last_seen`; the partner can read it; non-partners cannot.
  - [ ] Schema or API test: no endpoint or column allows disabling sharing.
  - [ ] Frontend: privacy settings show disabled and unchangeable toggles; permission denied shows the correct state.
  - [ ] Manual: background updates on iOS and Android, battery check.

### Phase 4 exit gate
- [ ] Route-table scan and DB-privilege tests green.
- [ ] Two devices exchange photo, voice, and promise posts, and see live partner location and last seen.

---

## Phase 5: The Public Ledger & Monetization

**Decisions applied:** ledger searches by phone hash and name, shows "Fled the App" during the deletion cooldown; Divorce Fee through RevenueCat (fake validator and a dev-only "simulate purchase" until store accounts exist); refunds ignored for the MVP. Needs RevenueCat, App Store Connect, and Google Play Console only for real sandbox purchases. See [external-tool-need.md](./external-tool-need.md).

### 5A. Ledger search
- [ ] Migration adds a trigram index on `lower(display_name)` for name search (see [database.md](./database.md)).
- [ ] `POST /ledger/search` (name or phone). Phone search hashes the normalized input and compares to `phone_hash`. Name search returns only name matches that are public.
- [ ] Response: `locked` / `not_found` / `fled`, and partner display info as allowed. `fled` is returned for users in the 90-day deletion cooldown. Never returns hashes or raw phone numbers. Users who have been purged are `not_found`.
- [ ] Rate limiting and abuse controls (enumeration of phone numbers is the main risk): per-user and per-IP limits, auth required, daily cap.
- [ ] **Tests:**
  - [ ] API: locked user found by phone and by name; unknown returns `not_found`; a user in the deletion cooldown shows the `fled` placeholder state; a purged user is `not_found`.
  - [ ] Phone formats all resolve to the same hash match.
  - [ ] Rate limit and daily cap return 429.
  - [ ] Response allowlist test (no hashes or private fields).

### 5B. Social badges
- [ ] Server-side badge render (image) for the "Locked Status" with the partner names and date: `GET /relationship/badge.png`, or a client-side render with `react-native-view-shot`.
- [ ] Share sheet via `expo-sharing`. Public share URL with an Open Graph image (optional).
- [ ] "Fled the App" placeholder asset used when the user is `deactivating`.
- [ ] **Tests:**
  - [ ] Backend: badge endpoint returns a PNG with correct dimensions for users with an active relationship and 403/404 otherwise.
  - [ ] Frontend: share button opens the share sheet with the correct file (mocked); snapshot tests of the badge component for locked and fled states.
  - [ ] Ledger and profile photo swap to the placeholder when the partner is in the deletion cooldown.

### 5C. The escape hatch (Divorce Fee, one-sided exit)
- [ ] Fake purchase validator and a dev-only "simulate purchase" endpoint (blocked in production). Later: RevenueCat project, `react-native-purchases` in the app, and a consumable product (for example $19.99) configured in App Store Connect and Google Play Console. App user ID is our user UUID.
- [ ] `POST /divorce/purchase/verify` (and the RevenueCat webhook): confirm the transaction through the RevenueCat REST API, idempotent on `iap_transactions.provider_transaction_id` (unique). Use the fake validator in tests and local dev.
- [ ] On a valid purchase, in a single transaction: set the relationship `ended` with `ended_reason='divorce_fee'` and `ended_by_user_id`, flip `relationship_members.active`, write an `iap_transactions` row, and send the dramatic push to the partner. The vault and certificate move to Past Matches. Identity hashes stay.
- [ ] Refunds and chargebacks: decision is to **ignore** them for the MVP (the lock stays ended). Log them for review.
- [ ] **Tests:**
  - [ ] API with a fake validator: valid purchase ends the lock; replayed transaction is a no-op; invalid or forged purchase gets 402/400 and nothing changes.
  - [ ] DB: both users end up free and consistent; audit row written; partner notified; archive is readable by both.
  - [ ] Concurrency: double submit of the same transaction, and a divorce racing with a mutual breakup accept or a new bind attempt.
  - [ ] Route-table scan still passes: there is no route that deletes relationships.
  - [ ] Frontend: purchase UI states (loading, cancelled, failed, success); sandbox purchase on iOS (StoreKit) and Android (Play test track).

### Phase 5 exit gate
- [ ] Sandbox purchase ends a lock end to end on both platforms and the partner gets the push.
- [ ] Ledger abuse controls verified under load.

---

## 6. Go-live

### 6A. Swap in real providers (before real users)
The Phase 1 workarounds are development only. See also the swap-in checklist in [external-tool-need.md](./external-tool-need.md).
- [ ] **Spike (half a day):** in Stripe Identity **test mode**, confirm the verified outputs include the document number. If not, fall back to hashing `country + full name + date of birth` and bump `hash_version`. Record the result in `decisions.md`.
- [ ] Replace `dev_manual` with **Stripe Identity**: `POST /verification/sessions` creates a VerificationSession (document + selfie) and returns the client secret; `POST /verification/webhook` verifies the signature, hashes the document number, rejects duplicates (`ID_ALREADY_REGISTERED`), and is idempotent on `identity_verifications.provider_event_id`. App side: `@stripe/stripe-identity-react-native` (needs the dev build) replaces the upload screen behind the `IdentityStep` component.
- [ ] Replace the dev link delivery with real delivery: an SMS containing the same link (or Twilio Verify). Set `users.phone_verified_at`. Remove the link from API responses.
- [ ] Re-verify accounts with `verification_method = 'dev_manual'` (force the Stripe step on next login).
- [ ] Tests: Stripe webhook with a bad signature gets 401 and a replayed event is a no-op; the production guard rejects the dev providers.
- [ ] Apply for Stripe live-mode approval early because it can take days.

### 6B. Release readiness

- [ ] **Security review:** hash and pepper handling, JWT, webhook signature checks, IDOR checks on every `/{id}` route, rate limits, presigned URL scope, PII in logs.
- [ ] **Privacy and legal:** privacy policy, terms, consent records, data-subject request policy, age gate (18+), regional restrictions.
- [ ] **Store compliance:** account-deletion answer (free in-app deletion with the 90-day cooldown, found in privacy settings), location-permission justification strings, background location review, IAP review notes.
- [ ] **Performance and load:** k6 or Locust on bind, accept, and ledger endpoints. Load test the concurrency scenarios from Phase 2 at higher volume.
- [ ] **Observability:** Sentry (backend and app), metrics for lock attempts, rejected attempts, push delivery, ledger queries.
- [ ] **Deployment:** production compose or cloud config, secrets management (move `HASH_PEPPER` to AWS Secrets Manager), managed Postgres with backups and PITR, Upstash Redis, migration-on-deploy, a scheduler for the daily purge job, `APP_ENV=production` blocks seeding.
- [ ] **Builds:** EAS build profiles (`eas.json`) for preview and production, OTA update policy, versioning.
- [ ] **E2E smoke suite** (Maestro or Detox) covering: onboard, lock, breach alert, mutual breakup, account deletion and cancel, vault post, ledger search, divorce purchase (sandbox).

## 7. Suggested order of work (milestones)

| Milestone | Contents | Done when |
| --- | --- | --- |
| M0 | Sections 1 and 2 | CI green, test harnesses running |
| M1 | Phase 1 | A user can onboard on a device with no external accounts (link login and manual ID) |
| M2 | Phase 2 | Two users can lock and get a certificate; concurrency suite green |
| M3 | Phase 3 | Breach attempts are blocked and alert the partner; breakup, deletion cooldown and purge work; dev build running |
| M4 | Phase 4 | Vault and forced presence work between partners |
| M5 | Phase 5 | Ledger, badges, and divorce purchase work in sandbox |
| M6 | Section 6 | Real Stripe and SMS delivery in place; security, legal, and store review passed; release candidate |

## 8. Risks to track

- [ ] App Store / Play Store rejection (forced location tracking, public ledger, punitive deletion notifications). Mitigation: early policy review, consent screens, fallback design where tracking can be reduced.
- [ ] Legal exposure (public ledger of personal data, retention during the 90-day cooldown, GDPR/CCPA right to erasure, biometric laws). Mitigation: counsel review, consent logging, minimal data retention (hashes only, no images), a working purge job.
- [ ] Stripe Identity may not return the document number. Mitigation: the section 6A spike and the fallback hash input; `hash_version` allows a later change.
- [ ] Dev workarounds (typed ID number, link without phone proof) shipped by mistake would allow account takeover and fake IDs. Mitigation: production startup guard and its test; `verification_method` lets us find and re-verify those accounts.
- [ ] No face matching: the same person could verify with a different valid ID. Mitigation: accept for the MVP, revisit with a provider that returns a face template.
- [ ] Purge job failure leaves users locked past day 90. Mitigation: alert on job failure, make it idempotent, and test against due and not-due data.
- [ ] Pepper leak or loss. Mitigation: secret manager, rotation plan (versioned hash column), backup.
- [ ] Ledger scraping and stalking abuse. Mitigation: rate limits, auth, caps, audit logs.
- [ ] Background location battery and OS limits. Mitigation: early spike in Phase 4.
