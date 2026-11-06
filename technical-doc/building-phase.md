## Phase 1: Core Infrastructure & Identity (The Foundation)

Set up the React Native/Expo frontend and Python FastAPI backend monorepo. The priority here is establishing the irreversible identity layer before any pairing happens.

* **Database Schema:** Design the PostgreSQL tables with strict unique constraints on user pairs to physically prevent a user from having more than one active relationship row.
* **Identity Hashing:** Implement the ID scanning and phone number verification. Hash these identities immediately so the backend relies on immutable data, not just usernames.
* **Basic Onboarding:** Build the UI for biometric/ID capture and the initial user profile creation.

## Phase 2: The Permanent Lock (Mutual Consent)

Build the core pairing engine. This needs to be bulletproof to prevent race conditions where a user tries to lock with two people simultaneously.

* **Invite System:** Create the "Forever Bind" request flow using Redis to handle short-lived invites and rate limiting.
* **Warning Flow:** Build the aggressive, multi-screen "Point of No Return" UI for the receiving partner.
* **The Transaction:** Write the backend logic that officially locks the two hashed IDs together in the database and mints the digital "Marriage Certificate."

## Phase 3: The "Rage-Bait" Defenses (The Trap)

Implement the core restrictions that make the app viral and controversial.

* **Rejection Engine:** Build the logic that intercepts any new connection attempt by a locked user, throws the "already bound" error, and exposes the original partner's profile.
* **Snitch Notifications:** Integrate push notifications to instantly alert the original partner if a breach is attempted.
* **Undeletable State:** Remove all standard account deletion capabilities. Intercept deletion requests to simply log the user out or hide the interface, keeping the database lock intact.

## Phase 4: The Shared Vault & Transparency

Introduce the content and tracking features that users cannot opt out of.

* **The Vault:** Connect cloud storage to handle photo and voice note uploads for the shared timeline.
* **No-Delete Policy:** Ensure the frontend UI has no "Delete" buttons for vault posts and the FastAPI backend lacks any DELETE endpoints for this data.
* **Forced Tracking:** Implement the persistent "Last Seen" and location tags, hardcoding them to bypass standard privacy toggles.

## Phase 5: The Public Ledger & Monetization

Launch the social proof elements and the final escape hatch.

* **Ledger Search:** Build the API that allows anyone to query a phone number or name against the database to check a user's lock status.
* **Social Badges:** Generate the shareable "Locked Status" graphics for social media.
* **The Escape Hatch:** Implement the in-app purchase flow for the premium "Divorce Fee" (e.g., $19.99)—the only programmed way to execute a database row deletion and break the lock.