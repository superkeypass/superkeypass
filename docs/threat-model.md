# Threat model

Status: **draft**. Every scenario lists what we must protect, what the
attacker (or accident) has, and the intended defence. Open questions are
marked **OPEN** and are where review is most useful.

## Assets

| Asset | Why it matters |
|---|---|
| Vault item plaintext | The whole point. Bank, email, and health logins. |
| Vault keys (user key, item keys) | Whoever holds them holds the plaintext. |
| Recovery material (printed sheet, admin escrow share) | A second way to the keys — as sensitive as the keys. |
| Account metadata (sites, usernames, access log) | Reveals who banks where; enables phishing. |
| Alert channel | If an attacker can suppress alerts, tamper detection is theatre. |

## Actors

- **The user** — non-technical, reuses habits, may be socially engineered.
- **The admin** — trusted family member; also a single point of failure.
- **Opportunistic insider** — carer, visitor, relative, repair shop: short
  physical access, no special skill.
- **Remote attacker** — phishing, credential stuffing, server exploitation.
- **Server-level attacker** — has the host, the database, or a backup.

## Scenarios

### T1. Lost or stolen phone (locked)

- **Attacker has:** a locked device.
- **Must hold:** vault stays sealed; the user regains access without it.
- **Defence:** vault keys wrapped by the platform keystore (Secure Enclave /
  StrongBox / TPM) and released only on biometric/device-credential
  success. Admin can revoke the device remotely; revocation rotates the
  device's wrapping and invalidates its session. User re-enrols on a new
  device via admin-assisted recovery or the printed sheet.
- **OPEN:** does a device that is offline when revoked keep a usable cached
  vault? (Likely yes until it reconnects — document the window.)

### T2. Forgotten everything

- **User has:** nothing — no device, no memory of any secret.
- **Must hold:** they get back in; nobody *else* gets in the same way.
- **Defence:** two independent paths.
  - **Printed recovery sheet** — a high-entropy recovery key (words + QR),
    printed at setup, stored with the will / in a drawer. Scanning it on a
    new device, plus an out-of-band confirmation, restores access.
  - **Admin-assisted recovery** — the admin approves re-enrolment. The admin
    must *not* be able to read the vault unilaterally: approval releases an
    escrow share that is useless without a server-side share and a time delay.
- **OPEN:** the exact escrow construction (Shamir 2-of-3 across
  user-sheet / admin / server? time-locked?). See ADR 0001 dependencies.

### T3. Fifteen minutes with an unlocked phone or computer

The scenario this project most wants to get right, and the one most vaults
ignore: a carer, relative, or partner with brief access to an unlocked session.

- **Attacker has:** an unlocked session, no prior skill, limited time.
- **Likely actions:** bulk export; reveal many passwords in quick succession;
  add their own device or recovery method; disable alerts.
- **Defence:**
  - **Bulk export** requires fresh biometric/hardware-key re-auth *and*
    fires an alert before it completes. Optionally a delay (e.g. 24h) with
    cancel-by-any-trusted-contact.
  - **Mass-reveal detection** — the client counts reveals/copies per window;
    crossing a threshold (e.g. >5 in 2 minutes) fires a tamper alert and
    requires re-auth for further reveals.
  - **Security-setting changes** (add device, change recovery, change or
    mute alert contacts) require re-auth, are delayed, and notify *all*
    trusted contacts — including the ones being removed.
  - **Exposure report** — every reveal/copy/autofill/export is logged
    server-side with item id and time, so after an incident we can list
    exactly what was touched. See [feature ideas](feature-ideas.md).
- **Residual risk:** someone reading passwords off screen slowly, one at a
  time, under the threshold. The access log still records it, so the exposure
  report still covers it after the fact.
- **OPEN:** how to log reveals from a client the attacker controls? A reveal
  that never reaches the server is invisible. Mitigation: reveals require a
  server round-trip for a per-item key (costs offline access) — trade-off to
  decide.

### T4. Server compromise

- **Attacker has:** the database, the host, or a backup.
- **Must hold:** no plaintext; no offline-crackable master password (there
  is none by default, so nothing to brute-force).
- **Defence:** zero-knowledge storage; keys never leave clients unwrapped;
  server's escrow share alone is insufficient. Access logs and alert
  configuration are integrity-protected (signed by clients) so a server
  attacker can't silently rewrite history.
- **Residual risk:** a *live* compromised server can serve malicious web
  client code. Prefer native/installed clients; a web vault, if any, must be
  treated as higher risk.
- **OPEN:** can the server suppress alerts? Alerts that the server sends
  can be dropped by a compromised server. Consider client-side fan-out
  (push via a second channel) for the most critical alerts.

### T5. Admin gone

- **Situation:** the admin dies, moves on, loses interest, or loses their own
  access. The server keeps running until it doesn't.
- **Must hold:** family members keep access and can migrate away.
- **Defence:** a designated **successor admin**; the printed sheet works
  without the admin; standard-format export for each user; server backup
  documented in a one-page "if I'm gone" sheet produced at setup.
- **OPEN:** what happens to the server itself (hosting bill, domain)? Out of
  scope for software, in scope for the setup checklist.

### T6. Phishing and fake recovery

- **Attacker has:** the user's trust and a phone number.
- **Likely action:** "Hi Mum, I'm the admin, read me the code on your sheet."
- **Defence:** the recovery sheet says, in large type, that nobody will ever
  ask for it. Recovery codes are scanned, not read aloud. Admin approval
  happens in-app, never via a code the user relays. Passkeys/WebAuthn origin
  binding for web login.

## Out of scope (for now)

- Nation-state attackers and malware with root on the user's device — a
  keylogger on an unlocked machine sees what the user sees.
- Coercion of the user or admin.
- Side channels on the platform keystores themselves.
