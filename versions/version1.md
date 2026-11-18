# Version 1: Two singles lock in

Goal: the smallest end-to-end version of the core idea. Two people create accounts, one invites the other with a link, the other accepts, and both see the same "locked" screen.

**Not in v1:** SMS or phone verification, ID verification, push notifications, Twilio, Stripe, vault, ledger, breakup, Divorce Fee, account deletion. No external services. Everything runs on our own backend (FastAPI + Postgres) and the Expo app.

## Identity in v1

- An account is **phone number + password**. The phone number is the identity: one account per phone number.
- The phone number is **not verified** in v1. Verification (SMS) comes in a later version. Until then, the `phone_verified_at` field stays empty.
- The phone is normalized to E.164 (`+14155550100`) before it is used, so `(415) 555-0100` and `+1 415 555 0100` are the same account.
- Passwords are stored only as a slow hash (argon2 or bcrypt). Never the plain password.
- ID verification is not required. It returns later as an optional "Verified Lock" upgrade.

## The main flow

### 1. User A signs up
1. A opens the app and taps **Create account**.
2. A enters phone number A and a password, then a first and last name.
3. A lands on the **Single** home screen: "You're not locked to anyone yet." with a **Lock in with someone** button.

### 2. User B signs up
Same as A, with phone number B. B also lands on the **Single** home screen.

### 3. A invites B
1. A taps **Lock in with someone**.
2. The app creates an invite and shows a share sheet with a link, for example `projectlock://invite/<token>` (plus a web fallback URL later).
3. A sends the link to B any way they like (iMessage, WhatsApp, etc.).
4. A's home screen now shows **Waiting for someone to accept** with a countdown to expiry and a **Cancel invite** button.

### 4. B opens the link
1. B taps the link. The app opens on the **Invite** screen.
   - If B is not logged in, B logs in or signs up first, then lands back on the invite automatically.
2. The Invite screen shows: "**A** wants to lock in with you." with A's display name, plus **Accept** and **Decline**.
3. Before accepting, B sees one clear confirmation step: "Locking is permanent. Are you sure?" (the full multi-screen warning flow comes later).

### 5. B accepts
1. B taps **Accept** and confirms.
2. The server checks that the invite is still valid and that neither A nor B is already locked, then creates the lock in one database transaction.
3. B sees the **Locked** screen.
4. Next time A opens the app (or refreshes the home screen), A sees the same **Locked** screen.

### 6. Both see the same thing
The **Locked** home screen for both users shows:
- Both display names ("A 🔒 B").
- The date and time they locked.
- "Locked for N days" counter.

## Edge cases v1 must handle

### Invite link TTL
- An invite expires **24 hours** after it is created.
- The invite token is a long random value. Only its hash is stored on the server.
- Opening an expired link shows "**This invite has expired.** Ask A to send a new one." No accept button.
- A sees the invite marked **Expired** on the home screen and can create a new one.
- A has **at most one open invite** at a time. Creating a new one cancels the old one, and the old link then shows "This invite is no longer valid."

### Both send links to each other
A and B may each send an invite at the same time. Rules:
- Whoever accepts first creates the lock. In the same transaction, **every other open invite from or to A or B is closed** (status `superseded`).
- If B accepts A's invite, then A later opens B's link, A sees "**You're already locked with B.**" and a button to the Locked screen, not an error.
- If A and B both tap Accept on each other's links at the same moment, the database allows only one lock: the second request gets "You're already locked with B." and shows the Locked screen. There is never a duplicate lock.
- Because the link is not tied to a phone number, A's link could also reach someone else, C. The first person to accept wins. Anyone else who opens it then sees "This invite is no longer available."

### B declines
- B taps **Decline**. The invite closes with status `declined`.
- A's home screen shows "**B declined your invite.**" the next time A opens or refreshes the app, and A can create a new invite.
- Opening a declined link again shows "This invite is no longer valid."

### Notifying the sender (no push in v1)
v1 has no push notifications. A learns what happened from the invite status on the home screen, which the app refreshes when it opens and every few seconds while A is on the waiting screen:

| Invite status | What A sees |
| --- | --- |
| `pending` | Waiting for someone to accept (countdown) |
| `accepted` | Locked screen with B |
| `declined` | "B declined your invite." Create a new one. |
| `expired` | "Your invite expired." Create a new one. |
| `cancelled` | Back to the Single home screen |
| `superseded` | Locked screen (A got locked through another invite) |

Push notifications replace the polling in a later version.

### Other small cases
- **A opens A's own link:** "This is your invite. Send it to the person you want to lock in with." No accept button.
- **A cancels the invite:** status `cancelled`. Opening the link shows "This invite is no longer valid."
- **B is already locked to someone else:** B sees "You're already locked." and cannot accept.
- **A got locked through another invite before B accepts:** B sees "This invite is no longer available."

## What v1 builds

### Backend
- Tables `users`, `refresh_tokens`, `invites`, `relationships`, `relationship_members`. Full schema: [database.md](../technical-doc/database.md) (Version 1). Invites are stored in **Postgres, not Redis**, for v1: fewer moving parts and the audit trail comes for free.
- Endpoints: sign up, log in, refresh, `GET /me` (includes lock state), create invite, view invite by token, accept, decline, cancel, get my current invite.
- The accept transaction locks both user rows in a fixed order, re-checks that both are free, creates the relationship, marks the invite `accepted`, and marks all other open invites from or to either user `superseded`.

### Frontend
- Screens: Sign up, Log in, Single home, Waiting (invite sent), Invite (accept or decline), Confirm, Locked home, plus the message states above.
- Deep link handling for `projectlock://invite/<token>`, including "log in first, then come back to the invite".

### Must-have tests
- Same phone in different formats cannot create two accounts.
- Expired, cancelled, declined, and superseded invites cannot be accepted.
- Both users send invites and both accept at once: exactly one lock.
- A's link accepted by B and by C at once: exactly one lock.
- Accepting your own invite is rejected.

## Known gaps in v1 (accepted for now)

- **Unverified phone numbers:** anyone can sign up with someone else's number and block it. Fixed when SMS verification arrives.
- **No password reset:** without SMS there is no way to prove you own the number. A dev-only reset is enough for testing.
- **No way to unlock:** v1 has no breakup. Add a dev-only "unlock" endpoint so we can test repeatedly.
- **App not installed:** a `projectlock://` link does nothing if B doesn't have the app. For v1 both testers install the app first. A web fallback page comes later.
