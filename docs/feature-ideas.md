# Feature ideas

Candidate features, roughly in the order they matter to the target user.
Nothing here is committed; each will get a design doc or ADR before it's built.
Cross-references point at the [threat model](threat-model.md).

## 1. Tamper alert

Detect the "fifteen minutes with an unlocked device" pattern (T3) and tell
the people who can act.

**Triggers**
- Mass reveal: more than *N* passwords revealed or copied within *M* minutes
  (defaults ~5 in 2 min; tunable per user).
- Bulk export started.
- New device enrolled, recovery method changed, alert contacts changed.
- Unlock from a new location/network at an unusual hour (low-confidence
  signal — informational only).

**Response**
- Immediate re-auth required for further reveals.
- **Fan-out** to the user's trusted contacts (admin plus one or two others):
  push, email, SMS. At least one channel must not depend on the server alone
  (T4 OPEN).
- One-tap actions in the alert: *It was me* / *Lock the vault* / *Revoke
  that device*.

**Open questions:** threshold defaults that don't cry wolf during a
legitimate "move everything to a new laptop" session; how to pre-declare
such a session.

## 2. Exposure report

After an incident, answer "what do I change, and in what order?"

- Pull every access event (reveal, copy, autofill, export) in a time window
  — default: from the last known-good moment to now.
- Rank items by damage if leaked: financial & email first (email resets
  everything else), then health/government, then shopping, then the rest.
  Boost items that are reused elsewhere or lack 2FA.
- Output a **rotation checklist**: item, why it's ranked here, direct link to
  the site's change-password page, a tick box. Printable.
- Works for the admin on the user's behalf, with the user's consent.

## 3. Printed recovery sheet generator

- Generated at setup: recovery key as a word list + QR code, user's name,
  server URL, admin contact, date.
- Big-type warning: *Nobody from SuperkeyPass or your family will ever ask
  you to read this out.*
- Instructions a non-technical person can follow on a brand-new phone.
- Re-issue invalidates the old sheet; the app shows the sheet's issue date so
  a stale copy is recognisable.
- Optional second page: the "if the admin is gone" sheet (T5).

## 4. Admin-assisted recovery

- User on a new device taps *I'm locked out*; the admin gets an in-app request
  showing device, location, and time.
- Admin verifies out-of-band (a video call, in person) and approves.
- Cryptographically, approval releases an escrow share that is **not
  sufficient on its own** to read the vault (T2). Candidate: Shamir 2-of-3
  over {printed sheet, admin, server-with-time-lock}.
- Mandatory waiting period (e.g. 24–48h) during which the user's *other*
  devices and trusted contacts are notified and can cancel. Skippable only
  with a second trusted contact's approval.

## 5. Fingerprint-key support

- FIDO2/WebAuthn security keys with built-in fingerprint readers (e.g.
  YubiKey Bio, Feitian BioPass) as a first-class unlock method.
- Uses the PRF/hmac-secret extension to derive a key-wrapping key, so the key
  genuinely unlocks the vault rather than just gating a login.
- Ideal for users without a biometric phone/laptop, or who want a single
  physical "key to the vault" on their keyring.
- Enrol two keys; the backup lives with the recovery sheet.

## Parking lot

- Family sharing collections (shared streaming, utilities, Wi-Fi).
- Digital legacy: time-delayed access for a named heir.
- "Health check" for the admin: who has reused passwords, who hasn't
  unlocked in 90 days, who has no recovery method.
