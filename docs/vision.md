# Vision

## The problem

Password managers are built by and for people who like password managers.
They assume you will remember one strong master password forever, keep an
emergency kit somewhere sensible, and notice when something is wrong.

The people who most need a vault — parents and grandparents with dozens of
accounts, reused passwords, and a sticky note on the monitor — are exactly the
people those assumptions fail. When they forget the master password, the vault
is gone. When the phone is lost, so is the second factor. When the relative
who set it up moves away, nobody can help.

## Who it's for

**Primary user: a 50–80-year-old** who did not choose a password manager and
will not read a manual. They are set up — in person, once — by a family member.
Success is that they never think about SuperkeyPass again: logins autofill,
unlocking is a face or a fingerprint, and a lost phone is an inconvenience, not
a catastrophe.

**The admin: the tech-savvy relative** (adult child, grandchild, sibling) who
runs the server, enrols the family, and is the first call when something goes
wrong. They are competent but busy; they need recovery to be a two-minute job,
and they need to be told — loudly — when something suspicious happens.

**Not the target (for now):** enterprises, teams with SSO/SCIM needs, and power
users who want every knob. They are well served elsewhere.

## Principles

1. **No memorized secrets.** Nothing in the everyday or recovery path depends
   on the user remembering anything. Unlock is biometric or a hardware key;
   recovery is a printed sheet and/or a trusted admin. A master password may
   exist as an *option*, never a requirement.
2. **Recovery is a feature, not an apology.** Every way in is designed up
   front — lost device, forgotten everything, admin unavailable — with the
   same care as the way in. See the [threat model](threat-model.md).
3. **Loud when it matters, silent otherwise.** Normal use produces no
   prompts. Abnormal use (mass reveal, bulk export, new device at 3am)
   produces alerts to the people who can act on them.
4. **One live server.** A family runs one server. No cluster, no mandatory
   cloud, no background services to babysit. A Raspberry Pi or a $5 VPS is
   enough. Backups are one file.
5. **No vendor lock-in.** Standard export formats, documented storage, and
   compatibility with existing clients where it doesn't compromise the
   principles above. Leaving must be as easy as arriving.
6. **Open source, AGPL.** The server, clients, and crypto are auditable. A
   modified server run for others must share its changes.
7. **Zero-knowledge server.** The server stores ciphertext. A stolen server
   disk must not yield vault contents.

## Non-goals

- Replacing Bitwarden/1Password for organisations.
- Being the first to support every new credential type — passkey support
  matters, but reliability for the target user matters more.
- A hosted SaaS offering (at least initially). Self-hosting is the product.

## What success looks like

- Grandma unlocks with her face for a year and never sees a password prompt.
- She drops her phone in a lake; the admin restores her in under ten minutes,
  or she does it herself from the printed sheet.
- A carer copies her vault from an unlocked laptop; within a minute her
  daughter's phone buzzes, and the exposure report lists the bank login first.
