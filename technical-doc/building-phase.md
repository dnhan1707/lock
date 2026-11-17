## Phase 1: Core Infrastructure & Identity (The Foundation)

Set up the React Native/Expo frontend and Python FastAPI backend monorepo. The priority here is establishing the irreversible identity layer before any pairing happens.

* **Database Schema:** Design the PostgreSQL tables so a user can have at most one active relationship (a partial unique index on active `relationship_members` rows). Ended relationships are archived, never deleted.
* **Identity Hashing:** Implement ID verification and phone verification. Hash these identities immediately (HMAC with a server-side pepper) so the backend relies on immutable data, not just usernames. No face hash in the MVP (see [decisions.md](./decisions.md)).
* **Basic Onboarding:** Build the UI for ID capture and the initial user profile creation.

## Phase 2: The Permanent Lock (Mutual Consent)

Build the core pairing engine. This needs to be bulletproof to prevent race conditions where a user tries to lock with two people simultaneously.

* **Invite System:** Create the "Forever Bind" request flow using Redis to handle short-lived invites and rate limiting.
* **Warning Flow:** Build the aggressive, multi-screen "Point of No Return" UI for the receiving partner.
* **The Transaction:** Write the backend logic that officially locks the two hashed IDs together in the database and mints the digital "Marriage Certificate."

## Phase 3: The "Rage-Bait" Defenses (The Trap)

Implement the core restrictions that make the app viral and controversial.

* **Rejection Engine:** Build the logic that intercepts any new connection attempt by a locked user, throws the "already bound" error, and exposes the original partner's profile.
* **Snitch Notifications:** Integrate push notifications to instantly alert the original partner if a breach is attempted.
* **Undeletable State:** Account deletion is free but delayed. A deletion request starts a 90-day cooldown: the account is hidden, the lock stays active, the partner is notified, and logging in cancels it. A daily purge job wipes the hashes and profile at day 90 and frees the partner.
* **Mutual Breakup:** Free exit with a 72-hour window. The relationship is archived into "Past Matches".

## Phase 4: The Shared Vault & Transparency

Introduce the content and tracking features that users cannot opt out of.

* **The Vault:** Connect cloud storage to handle photo and voice note uploads for the shared timeline.
* **No-Delete Policy:** Ensure the frontend UI has no "Delete" buttons for vault posts and the FastAPI backend lacks any DELETE endpoints for this data.
* **Forced Tracking:** Implement the persistent "Last Seen" and location tags, hardcoding them to bypass standard privacy toggles.

## Phase 5: The Public Ledger & Monetization

Launch the social proof elements and the final escape hatch.

* **Ledger Search:** Build the API that allows any signed-in, verified user to query a phone number or name against the database to check a user's lock status.
* **Social Badges:** Generate the shareable "Locked Status" graphics for social media.
* **The Escape Hatch:** Implement the in-app purchase flow for the premium "Divorce Fee" (e.g., $19.99), the only way to end the lock one-sided. It archives the relationship (`ended_reason='divorce_fee'`) and pushes the partner. No relationship rows are deleted.