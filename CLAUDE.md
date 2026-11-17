# GX Display Shop — order 3D-printed store displays

**App key: `displayshop`** (`.gx_app`). Repo `greencross-displayshop`, GitHub Pages
(`https://greencrosscanna.github.io/greencross-displayshop/`). Standalone app; staff reach it from the
Staff Portal tile. Built 2026-11-16 from the Order Catalog in Dropbox (`GC Marketing/3D Print/Order Catalog`).

## What it is

A catalog of displays Sky prints in-house — stands, bottle and jar holders, trays, lighter and battery
displays, brand name plates (plus a custom-text plate). A manager builds an order and **Place order**
emails it to Sky. There is no order sheet, no inventory and no print queue: Sky confirms timing by hand.

- **Who gets in:** anyone with at least one app grant. There is no `displayshop` grant row needed —
  GX Core's `gxRoleForApp_` gives a person their HIGHEST role from any other app. An explicit
  `displayshop` row in `app_access` overrides that for one person.
- **Who can order:** manager, director, editor or admin (that derived role). Anyone else can browse and
  gets "Copy list for your manager" instead of Place order. The server enforces this; the page only mirrors it.
- **The order route:** `POST ?action=submit_display_order` on GX Core (text/plain JSON). The page sends
  `{session, store (store_id), needBy, notes, lines:[{sku,name,variant,qty}], text}`. GX Core takes the
  orderer and their email from the session, checks the store, the skus (`GX_DSHOP_SKUS_`), 1–40 lines,
  qty 1–99, rate-limits 6/hour/person, writes one `audit_log` row, and emails Sky. Never retried: a
  timed-out POST may already have been emailed.
- **Stores:** live from `?action=stores` (registry display names: Century, Center, Commercial, Baseline,
  Portland, River); the list in `template.html` is only the offline fallback.

## Layout

| File | Role |
|---|---|
| `template.html` | the page source: CSS, sign-in, catalog UI, checkout. `__DATA__`/`__IMG__`/`__FONT__` are filled at build |
| `catalog.json`, `plates.json` | products, variants, specs; brand plates |
| `img/` | product renders (`-dim` = dimension drawings) |
| `scripts/build_catalog.py` | builds **`index.html`** (self-contained, ~3.9 MB). Needs Pillow |
| `scripts/gen_sku_allowlist.py` | regenerates GX Core's `GX_DSHOP_SKUS_` from `catalog.json` |
| `scripts/make_catalog.py`, `stands_catalog.py`, … | generate `catalog.json` and the renders |

**`index.html` is a build output and IS the app.** Edit `template.html`/`catalog.json`, then
`python3 scripts/build_catalog.py`, and commit both.

**Adding an orderable product or size is a GX Core change:** run `python3 scripts/gen_sku_allowlist.py
--write`, which edits the hub's `gx_core.gs`; that ships with a library cut (Sky's word). Until then the
server refuses the new sku. A new **brand plate** needs no hub change (any `PLATE-<letters/digits>` is accepted).
The hub's `tests/display_order_test.js` fails when the two drift.

## Local dev

From the hub, `preview_start displayshop-preview` (port **8757**). `gx-dev.js` blocks the order write
until armed. `sh ./gxdevlogin.sh` does not know `displayshop` yet; mint a `core-admin` dev session and put
its token in `sessionStorage['displayshop_session']` (it is a viewer, so ordering is refused — by design).

The shop keeps its own dark CSS for its own classes; the sign-in gate uses gx-theme's shared `gx-login`
components. Never restyle a `gx-*` class here — send core-admin a note instead.

## Shipping

Bump `APP_VERSION` in `template.html` (vMAJOR.BBB), rebuild, commit, then `./deploy.sh` (records the
release). Features on a `feat/…` branch + PR the session merges when green; small fixes direct to `main`.
A deploy needs Sky's word.

## Known gaps

- Google sign-in is not offered here (the portal's Google client is not authorized for this origin).
- Jar sizes and the Pre-Roll Tube Holder are not yet test printed at every size; battery holder lettering
  renders black.
- Gift Card Stand and Dab Case Riser are "coming soon" and cannot be ordered.
