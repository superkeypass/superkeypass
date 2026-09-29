"""Printed recovery sheet (feature idea 3), v0 for stock Vaultwarden.

With Vaultwarden the master password still exists (ADR 0001, consequence 1),
so the sheet is where it lives: handwritten in a box, never typed into this
service, printed and kept with the family's important papers. The companion
fills in everything else — server address, admin contact, and what to do on a
new phone — and warns, in large type, that nobody will ever ask for it.
"""

from __future__ import annotations

import html
from datetime import date

import segno

from .config import Config
from .vw import User


def render(cfg: Config, user: User, today: date | None = None) -> str:
    today = today or date.today()
    e = html.escape
    qr = segno.make(cfg.vault_url, error="m").svg_inline(scale=4, dark="#111")
    name = e(user.name or user.email)
    admin = " · ".join(e(x) for x in (cfg.admin_name, cfg.admin_phone, cfg.admin_email) if x)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Recovery sheet — {name}</title>
<style>
  @page {{ size: letter; margin: 14mm; }}
  body {{ font: 15px/1.45 Georgia, "Times New Roman", serif; color:#111; background:#fff; max-width: 46rem; margin: 0 auto; padding: 16px; }}
  h1 {{ font-size: 26px; margin: 0 0 4px; }}
  .sub {{ color:#444; margin:0 0 18px; }}
  .warn {{ border: 3px solid #111; padding: 12px 16px; font-size: 20px; font-weight: bold; margin: 0 0 18px; }}
  .row {{ display:flex; gap: 24px; align-items:flex-start; }}
  .box {{ border: 1.5px solid #111; height: 44px; margin: 4px 0 14px; }}
  dt {{ font-weight: bold; margin-top: 8px; }}
  dd {{ margin: 0 0 4px; }}
  ol li {{ margin-bottom: 6px; }}
  .foot {{ margin-top: 22px; font-size: 12px; color:#555; }}
  .print {{ margin: 0 0 16px; }}
  @media print {{ .print {{ display:none; }} }}
</style></head>
<body>
<button class="print" onclick="window.print()">Print this sheet</button>
<h1>Password vault — recovery sheet</h1>
<p class="sub">For <strong>{name}</strong> ({e(user.email)}) · {e(cfg.family_name)} · issued {today:%B %-d, %Y}</p>

<div class="warn">Nobody from SuperkeyPass, the bank, or the family will ever ask you
to read this sheet out loud, over the phone, or by text. If someone asks, it is a scam.
Hang up.</div>

<div class="row">
  <div style="flex:1">
    <dl>
      <dt>Vault address</dt><dd>{e(cfg.vault_url)}</dd>
      <dt>Your sign-in email</dt><dd>{e(user.email)}</dd>
      <dt>Who to call for help</dt><dd>{admin or "&nbsp;"}</dd>
    </dl>
  </div>
  <div>{qr}<div style="font-size:12px;text-align:center">Scan to open the vault</div></div>
</div>

<p><strong>Master password</strong> — write it by hand. Do not type it anywhere else.</p>
<div class="box"></div>
<p><strong>Two-step login recovery code</strong> — from Settings → Security → Two-step login → View recovery code.</p>
<div class="box"></div>

<h2 style="font-size:18px">If you get a new phone or computer</h2>
<ol>
  <li>Install the <strong>Bitwarden</strong> app from the App Store or Google Play.</li>
  <li>On the sign-in screen choose <strong>Self-hosted</strong> and enter the vault address above.</li>
  <li>Sign in with your email and the master password written on this sheet.</li>
  <li>Turn on Face ID / fingerprint unlock when the app offers it.</li>
  <li>Call the person listed above so they know you're set up again.</li>
</ol>

<p class="foot">Keep this sheet with your will or other important papers. A newer sheet
replaces this one — destroy old copies. Issued {today.isoformat()}.</p>
</body></html>"""
