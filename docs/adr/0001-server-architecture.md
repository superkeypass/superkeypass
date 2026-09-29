# ADR 0001: Server architecture — fork, build, or companion?

- **Status:** Proposed — **awaiting a decision**. Options are laid out below;
  nothing has been chosen.
- **Date:** 2026-09-28

## Context

SuperkeyPass needs a server that stores encrypted vaults, handles device
enrolment and recovery, logs access events, and fans out alerts. The features
that make it different — no memorized master password, admin-assisted
recovery with escrow, mass-reveal detection, exposure reports — touch the key
hierarchy and the client/server protocol, not just the UI.

[Vaultwarden](https://github.com/dani-garcia/vaultwarden) (AGPL-3.0, Rust) is
a mature, lightweight, single-binary reimplementation of the Bitwarden server
API. It runs happily on a Raspberry Pi and is loved by self-hosters — which is
our deployment model exactly. Its clients are Bitwarden's official apps.

The tension: Bitwarden's protocol is built around a **master password** (it
derives the master key that wraps the user key). Our first principle is that
no one has to remember one.

## Options

### A. Fork Vaultwarden and extend it

Add our endpoints (access log, alerts, escrow recovery) to a fork.

- ➕ Inherits a working, audited-in-practice server: sync, orgs, attachments,
  2FA, WebAuthn, admin panel, backups.
- ➕ Official Bitwarden clients work on day one for the vault basics.
- ➖ The official clients know nothing about our features. Tamper alerts and
  exposure reports need client-side hooks (counting reveals) — so we'd need to
  fork the **Bitwarden clients** too (GPL-3.0, large TypeScript monorepo).
  That's the real cost, and it's big.
- ➖ Master password stays at the protocol's core. Bitwarden has added
  passkey-login and trusted-device decryption (TDE), which may get us most
  of the way — needs a spike to confirm TDE works outside the enterprise/SSO
  flow and in Vaultwarden.
- ➖ Perpetual rebase burden against an upstream that tracks Bitwarden's
  moving API.

### B. Build a new server (and clients)

Design our own protocol around device-bound keys from the start.

- ➕ The key hierarchy is exactly what we want: no master password, escrow
  recovery and access logging designed in, not bolted on.
- ➕ Freedom to make reveals server-mediated if T3 needs it.
- ➖ By far the most work: server, crypto, sync, and **every client**
  (iOS, Android, desktop, browser extension, autofill integrations).
- ➖ Novel crypto design is where password managers go to die. Needs an
  external review before anyone trusts it with a bank password.
- ➖ Years to parity with what families expect (autofill everywhere).

### C. Companion service alongside unmodified Vaultwarden

Run stock Vaultwarden for the vault; a small SuperkeyPass service beside it
handles recovery orchestration, alert fan-out, and exposure reports, reading
Vaultwarden's events/logs.

- ➕ Smallest build; ships something useful soonest (alerts, recovery sheet,
  exposure reports on top of Vaultwarden's event log).
- ➕ No fork to maintain; families already on Vaultwarden can adopt it.
- ➖ Limited by what Vaultwarden exposes. Its event logging is an org-level
  feature; individual reveal/copy events are client-side and may never reach
  the server — mass-reveal detection may be impossible without client changes.
- ➖ Can't remove the master password: that lives in the protocol.
- ➖ Two moving parts for a "one live server" product (mitigated by shipping
  one docker-compose).

## Suggested way to decide

These aren't exclusive in time. A plausible path: **C first** (prove alerts,
recovery sheet, and exposure reports on stock Vaultwarden; learn what data we
can and can't see), with two time-boxed spikes that decide what comes next:

1. Does Bitwarden's trusted-device decryption / passkey unlock work with
   Vaultwarden for a personal (non-SSO) account, eliminating the everyday
   master password? If yes, A becomes much cheaper.
2. Which access events do official clients report to the server? If reveals
   are invisible, T3 detection requires client changes → A or B.

## Decision

_Not yet made._ To be filled in by the maintainer after reviewing the options.

## Consequences

_To be written once a decision is made._
