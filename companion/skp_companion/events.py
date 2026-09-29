"""Vaultwarden / Bitwarden event types the companion cares about.

Codes mirror `EventType` in vaultwarden `src/db/models/event.rs`.

Cipher client events (1107–1117) are only stored for items that belong to an
organization, and only when Vaultwarden runs with ORG_EVENTS_ENABLED=true.
A family's items must therefore live in the family organization for tamper
detection to see them (see companion/README.md).
"""

from enum import IntEnum


class Ev(IntEnum):
    USER_LOGGED_IN = 1000
    USER_CHANGED_PASSWORD = 1001
    USER_UPDATED_2FA = 1002
    USER_DISABLED_2FA = 1003
    USER_RECOVERED_2FA = 1004
    USER_FAILED_LOGIN = 1005
    USER_FAILED_LOGIN_2FA = 1006
    USER_EXPORTED_VAULT = 1007

    CIPHER_VIEWED = 1107
    CIPHER_PASSWORD_SHOWN = 1108
    CIPHER_HIDDEN_FIELD_SHOWN = 1109
    CIPHER_CARD_CODE_SHOWN = 1110
    CIPHER_PASSWORD_COPIED = 1111
    CIPHER_HIDDEN_FIELD_COPIED = 1112
    CIPHER_CARD_CODE_COPIED = 1113
    CIPHER_AUTOFILLED = 1114
    CIPHER_CARD_NUMBER_SHOWN = 1117


# A secret left the vault's protection: shown on screen or put on the clipboard.
REVEALS = frozenset({
    Ev.CIPHER_PASSWORD_SHOWN,
    Ev.CIPHER_HIDDEN_FIELD_SHOWN,
    Ev.CIPHER_CARD_CODE_SHOWN,
    Ev.CIPHER_CARD_NUMBER_SHOWN,
    Ev.CIPHER_PASSWORD_COPIED,
    Ev.CIPHER_HIDDEN_FIELD_COPIED,
    Ev.CIPHER_CARD_CODE_COPIED,
})

# Every event that says an item was touched — the exposure report's input.
TOUCHES = REVEALS | {Ev.CIPHER_VIEWED, Ev.CIPHER_AUTOFILLED}

# Account-security changes that always alert.
SECURITY_CHANGES = frozenset({
    Ev.USER_CHANGED_PASSWORD,
    Ev.USER_DISABLED_2FA,
    Ev.USER_RECOVERED_2FA,
})

# How bad it is if this action happened in the wrong hands; ranks the report.
EXPOSURE_WEIGHT = {
    **{t: 3 for t in REVEALS},
    Ev.CIPHER_AUTOFILLED: 2,  # the site was logged into, secret not shown
    Ev.CIPHER_VIEWED: 1,      # item opened, secrets still masked
}

LABEL = {
    Ev.CIPHER_VIEWED: "viewed",
    Ev.CIPHER_PASSWORD_SHOWN: "password shown",
    Ev.CIPHER_HIDDEN_FIELD_SHOWN: "hidden field shown",
    Ev.CIPHER_CARD_CODE_SHOWN: "card code shown",
    Ev.CIPHER_CARD_NUMBER_SHOWN: "card number shown",
    Ev.CIPHER_PASSWORD_COPIED: "password copied",
    Ev.CIPHER_HIDDEN_FIELD_COPIED: "hidden field copied",
    Ev.CIPHER_CARD_CODE_COPIED: "card code copied",
    Ev.CIPHER_AUTOFILLED: "autofilled",
    Ev.USER_CHANGED_PASSWORD: "master password changed",
    Ev.USER_DISABLED_2FA: "two-step login disabled",
    Ev.USER_RECOVERED_2FA: "two-step login recovered",
    Ev.USER_EXPORTED_VAULT: "vault exported",
}
