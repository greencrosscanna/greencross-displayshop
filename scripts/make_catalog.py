"""Rebuilds the four angled-stand products in catalog.json from models/_meta.json (real bounding boxes).
Run after stands_catalog.py: python3 make_catalog.py"""
import json, os
C = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import glob
meta = {}
for f in glob.glob(C + '/models/meta_*.json'): meta.update(json.load(open(f)))
cat = json.load(open(C + '/catalog.json'))
keep = [p for p in cat['products'] if p['id'] not in ('VAPE', 'MYLAR', 'BOTTLE', 'JAR', 'SIMPLE', 'BAG', 'TACO', 'PRICECARD', 'PREROLL', 'SOON-PRE')]

def mm(x): return '%g mm' % round(x, 1)
def inch(x): return '%.2f in' % (x / 25.4)
def both(x): return '%s (%g mm)' % (inch(x), round(x, 1))

ANG = [dict(id='30', label='30°', note='Lower shelves'), dict(id='45', label='45°', note='Mid shelves'), dict(id='75', label='75°', note='Top shelves')]
SHELF = {a['id']: a['note'] for a in ANG}

def dims(k):
    e = meta[k]['ext']; return [('Width', e[0]), ('Depth, front to back', e[2]), ('Height', e[1])]

def variant(k, vid, label, extra=None, img_key=None):
    sp = {'Face angle': k.split('-')[-1] + '° to the table', 'Best shelf': SHELF[k.split('-')[-1]]}
    if extra: sp.update(extra)
    for n, v in dims(k): sp[n] = mm(v)
    return dict(id=vid, label=label, img=img_key or k, dim=k + '-dim', specs=sp)

simple = dict(id='SIMPLE', cat='stands', name='Simple Stand', tag='Boxed and blister packs',
    blurb='A flat-base stand for boxed and blister packs. Vape cartridge boxes and boxed pre-rolls lean back on the angled face. Pick the angle for the shelf it goes on.',
    axes=dict(sizes=[dict(id='M', label='Medium')], angles=ANG),
    fits=['Sessions vape, blister, 5.5 in', 'Mule vape, box, 5.5 in', 'East Fork pre-roll, box, 4.75 in', 'Hellavated pre-roll, box, 4.5 in'],
    fitnote='Medium suits packs 4.5 to 5.5 in long. The stand back sits 1 in below the shortest pack so it hides behind the product.',
    variants=[variant('simple-' + a['id'], 'M-' + a['id'], 'Medium, %s (%s)' % (a['label'], a['note'].lower()), {'Stand back height': mm(89.0), 'Stand width': mm(37.5)}) for a in ANG],
    notes=['30° is for lower shelves, 45° for mid shelves, 75° for top shelves.'])

bag = dict(id='BAG', cat='stands', name='Edge Stand', tag='Mylar bags',
    blurb='A stand with a small front lip that catches the bottom seam of a mylar bag, so off-balance bags do not slide. Any product in a mylar bag goes here, vapes and pre-rolls alike.',
    axes=dict(sizes=[dict(id='M', label='Medium')], angles=ANG),
    fits=['Verdant vape, mylar, 5 in', 'Oregon Roots vape, mylar, 5.25 in'],
    fitnote='Medium suits bags 5 to 5.25 in long. The stand back sits 1 in below the shortest bag.',
    variants=[variant('bag-' + a['id'], 'M-' + a['id'], 'Medium, %s (%s)' % (a['label'], a['note'].lower()), {'Stand back height': mm(102.0), 'Stand width': mm(37.5), 'Front lip': '8 mm tall'}) for a in ANG],
    notes=['30° is for lower shelves, 45° for mid shelves, 75° for top shelves.'])

BOT = [('1oz', '1 oz', 30.0, ['1 oz tincture bottles']), ('4oz', '4 oz', 50.8, ['Magic 4 oz bottle, 2 in', 'Mule 4 oz bottle, 2 in']), ('8oz', '8 oz', 63.5, ['Magic 8 oz bottle, 2.5 in'])]
bvars = []
for sid, sl, dia, _ in BOT:
    for a in ANG:
        k = 'bottle-%s-%s' % (sid, a['id'])
        bvars.append(dict(variant(k, '%s-%s' % (sid, a['id']), '%s bottle, %s (%s)' % (sl, a['label'], a['note'].lower()), {'Bottle diameter': mm(dia), 'Cradle width': mm(meta[k]['w'])}), size=sid, angle=a['id'], fits=_))
bottle = dict(id='BOTTLE', cat='bottles', name='Bottle Stand', tag='Round bottles, 1 oz to 8 oz',
    blurb='A stand with a curved cradle that holds a round bottle upright against the angled face. Pick the bottle size and the shelf angle.',
    axes=dict(sizes=[dict(id=s, label='%s (%s bottle)' % (l, both(d))) for s, l, d, _ in BOT], angles=ANG),
    fitnote='Cradle is sized to the bottle diameter plus 2 mm.',
    variants=bvars, notes=['15° is for the lowest shelves, 30° for lower shelves.', 'Based on the Jar Holder 3 design (40.25 mm jar). The larger sizes come from changing its jar diameter parameter; test print one before ordering for all stores.'])

JAR = [('XS', 'Extra small', 40.25, ['Round jars and tins up to 40 mm']), ('S', 'Small', 50.0, ['Round jars and tins up to 50 mm']), ('M', 'Medium', 60.0, ['Magic 12 oz can, 2.25 in', 'Round gummy jars up to 60 mm']), ('L', 'Large', 70.0, ['Round tubs and cans up to 70 mm'])]
JANG = [dict(id='15', label='15°', note='Lowest shelves'), dict(id='30', label='30°', note='Lower shelves')]
SHELF.update({'15': 'Lowest shelves'})
jvars = []
for sid, sl, dia, _ in JAR:
    for a in JANG:
        k = 'jar-%s-%s' % (sid, a['id'])
        jvars.append(dict(variant(k, '%s-%s' % (sid, a['id']), '%s, %s jar, %s (%s)' % (sl, both(dia), a['label'], a['note'].lower()), {'Jar diameter': mm(dia)}), size=sid, angle=a['id'], fits=_))
jar = dict(id='JAR', cat='bottles', name='Jar Stand', tag='Jars, tins and cans',
    blurb='A solid block with a round pocket that holds a jar, tin or can on its side at an angle, label facing out. Pick the jar diameter and the shelf angle.',
    axes=dict(sizes=[dict(id=s, label='%s (%s)' % (l, both(d))) for s, l, d, _ in JAR], angles=JANG),
    fitnote='Built from your Jar Holder 3 design: the scoop matches the jar diameter, and the stand is the jar diameter plus 3.5 mm wide.',
    variants=jvars, notes=['15° is for the lowest shelves, 30° for lower shelves.', 'Based on the Jar Holder 3 design (40.25 mm jar). The larger sizes come from changing its jar diameter parameter; test print one before ordering for all stores.'])

cat['categories'] = [dict(id='stands', name='Stands'), dict(id='bottles', name='Bottles & jars'), dict(id='trays', name='Trays & holders'), dict(id='lighter', name='Lighters'), dict(id='battery', name='Battery holders'), dict(id='plates', name='Brand name plates'), dict(id='soon', name='Coming soon')]
taco = dict(id='TACO', cat='trays', name='Taco Tray', tag='Three-pocket tray',
    blurb='A red three-pocket tray that holds the Don Coolio Don Taco Case. Sits flat on the shelf or counter.', fits=['Don Coolio Don Taco Case'], fitnote='Made for the Don Coolio Don Taco Case.',
    variants=[dict(id='STD', label='', img='taco', dim='taco-dim', specs={'Pockets': '3', 'Width': '117.8 mm', 'Depth, front to back': '50 mm', 'Height': '32.6 mm', 'Colors': 'Red'})], notes=[])
card = dict(id='PRICECARD', cat='trays', name='Price Card Holder', tag='Shelf price card holder',
    blurb='A low black holder that sits flat on the shelf. A slot along the top grips a card upright, with GREENCROSS on the angled front.',
    variants=[dict(id='STD', label='', img='pricecard', dim='pricecard-dim', specs={'Length': '63.5 mm', 'Depth, front to back': '20.3 mm', 'Height': '7.6 mm', 'Colors': 'Black'})],
    notes=['Sold singly. Order one per card position.'])
pvars = []
for n in range(1, 11):
    for a in ANG:
        k = 'preroll-%d-%s' % (n, a['id'])
        pvars.append(dict(variant(k, '%d-%s' % (n, a['id']), '%d wide, %s (%s)' % (n, a['label'], a['note'].lower()), {'Tubes wide': str(n), 'Tube diameter': '18 mm'}), size=str(n), angle=a['id']))
pre = dict(id='PREROLL', hero='preroll-3-30', cat='stands', name='Pre-Roll Tube Holder', tag='Tubes lie in angled channels',
    blurb='An angled holder with one half-round channel per pre-roll tube and a front lip so the tubes do not slide off. Pick how many tubes wide (1 to 10) and the shelf angle.',
    axes=dict(sizes=[dict(id=str(n), label='%d wide' % n) for n in range(1, 11)], angles=ANG),
    fitnote='Each channel is sized for an 18 mm (0.71 in) tube up to 93 mm (3.7 in) long, on a 22 mm spacing.',
    variants=pvars, notes=['30° is for lower shelves, 45° for mid shelves, 75° for top shelves.', 'Built from your GCPreRollHolder Fusion design (18 mm tube, 93 mm long). Test print one before ordering for all stores.'])
cat['products'] = [simple, bag, pre, bottle, jar, taco, card] + keep
json.dump(cat, open(C + '/catalog.json', 'w'), indent=1)
print('catalog written:', [p['id'] for p in cat['products']])
