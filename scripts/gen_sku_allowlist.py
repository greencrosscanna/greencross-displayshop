"""Regenerate GX Core's Display Shop product allowlist (GX_DSHOP_SKUS_) from catalog.json.

GX Core's submit_display_order refuses any sku not in that list, so a NEW orderable product (or a new
size/angle) must be copied into the hub before managers can order it:

    python3 scripts/gen_sku_allowlist.py           # print the line
    python3 scripts/gen_sku_allowlist.py --write   # rewrite it in ../greencross-command-center/gx_core.gs

That is a GX Core change, so it ships with a library cut (./ship.sh), which needs Sky's word.
Brand name plates are NOT in the list (GX Core accepts any PLATE-<letters/digits>), so adding a brand
plate needs no hub change. The hub test tests/display_order_test.js fails if the two drift.
"""
import json, os, re, sys

C = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(os.path.dirname(C), 'greencross-command-center', 'gx_core.gs')
cat = json.load(open(os.path.join(C, 'catalog.json')))
skus = {p['id']: [v['id'] for v in p['variants']] for p in cat['products'] if not p.get('soon')}
line = 'const GX_DSHOP_SKUS_ = ' + json.dumps(skus, separators=(',', ':')) + ';'

if '--write' not in sys.argv:
    print(line)
    sys.exit(0)

src = open(HUB).read()
pat = re.compile(r'(// BEGIN GENERATED GX_DSHOP_SKUS_[^\n]*\n)const GX_DSHOP_SKUS_ = .*?;\n(// END GENERATED GX_DSHOP_SKUS_)', re.S)
if not pat.search(src):
    sys.exit('GX_DSHOP_SKUS_ markers not found in ' + HUB)
new = pat.sub(lambda m: m.group(1) + line + '\n' + m.group(2), src)
if new == src:
    print('already up to date')
else:
    open(HUB, 'w').write(new)
    print('updated', HUB)
