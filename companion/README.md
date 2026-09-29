# SuperkeyPass companion

A small service that runs next to an **unmodified Vaultwarden** (see
[ADR 0001](../docs/adr/0001-server-architecture.md)) and adds the parts of
SuperkeyPass that Vaultwarden doesn't have:

| Feature | What it does | Where |
|---|---|---|
| **Tamper alerts** | Watches for many passwords being revealed or copied within a couple of minutes, vault exports, and security changes (2FA off, master password changed), and alerts the family's trusted contacts by email and/or push. | background watcher |
| **Exposure report** | For a person and a time window, lists every item that was viewed, revealed, copied or autofilled, ranked so the secrets that were actually shown come first, with a link to open each one in the vault. Printable checklist. | `/skp/report?email=…` |
| **Recovery sheet** | A printable page with the vault address (plus a QR code), the admin's contact details, boxes to write the master password and 2FA recovery code by hand, new-phone steps, and a large anti-scam warning. | `/skp/sheet?email=…` |
| **Alert log** | Every alert raised, and which channels actually accepted it. | `/skp/api/alerts` |

Everything except `/skp/health` asks for the companion admin password
(HTTP Basic; any username, password = `SKP_ADMIN_TOKEN`).

## How it sees anything

The companion reads Vaultwarden's own `event` table, **read-only**. It never
sees vault contents: item names and passwords are end-to-end encrypted, which
is why the report shows item IDs with "open in vault" links, not names.

Two conditions have to hold, or it is blind:

1. **`ORG_EVENTS_ENABLED=true`** on Vaultwarden (set in `deploy/docker-compose.yml`).
2. **The family's items live in an organization.** Official Bitwarden
   clients report reveals, copies and autofills to the server, but
   Vaultwarden only records them for items owned by an organization. Items in
   someone's personal vault are invisible. Setup: create one organization for
   the family, give each person a collection, and move their items into it
   (or import straight into it).

Clients upload events in batches, roughly every minute, so an alert
arrives a minute or two after the burst, not instantly. A device that's
offline uploads when it reconnects; the companion tracks rows, not dates,
so late uploads are still checked.

## Run it

```bash
cd deploy
cp .env.example .env                        # fill in host, tokens, SMTP
cp companion.toml.example companion.toml    # fill in family + contacts
docker compose up -d
```

## Develop

```bash
cd companion
python3.12 -m venv .venv && .venv/bin/pip install -e '.[test]'
.venv/bin/pytest
```

## Known limits (v0)

- Master password still exists (Vaultwarden protocol). The recovery sheet is
  where it lives, handwritten. Removing it depends on the passkey /
  trusted-device spike in ADR 0001.
- Mass-reveal detection can't stop a reveal, only report it. Blocking needs
  client changes.
- The report can't rank a bank above a shopping site: it can't read names.
- Someone reading passwords slowly, under the threshold, won't trigger an
  alert, but still appears in the exposure report.
