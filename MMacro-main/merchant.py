"""Auto merchant: teleport to it when it arrives, read its shop with OCR, buy what's on the list."""
import difflib
import re
import time

import numpy as np

import game
import points

KNOWN_ITEMS = [
    "Void Coin", "Lucky Penny", "Gear A", "Gear B", "Mixed Potion",
    "Lucky Potion", "Lucky Potion L", "Lucky Potion XL",
    "Speed Potion", "Speed Potion L", "Speed Potion XL",
    "Fortune Spoid I", "Fortune Spoid II", "Fortune Spoid III",
    "Random Potion Sack", "Stella's Star", "Stella's Candle",
    "Rune of Wind", "Rune of Frost", "Rune of Rainstorm", "Rune of Hell",
    "Rune of Galaxy", "Rune of Corruption", "Rune of Nothing", "Rune of Everything",
    "Strange Potion I", "Strange Potion II", "Oblivion Potion",
    "Potion of Bound", "Merchant Tracker", "Heavenly Potion",
]
SLOTS = 5
TELEPORT_S = 2.0         # after Use, until we're close enough to talk
SHOP_SETTLE_S = 0.6      # longest we wait for the shop to fade in
OCR_THREADS = 2          # 2 is as accurate as 4 and uses less CPU

_reader = None


def wanted_from_text(text):
    """'Void Coin x5' per line -> {name: amount}, None means buy them all."""
    out = {}
    for line in (text or '').splitlines():
        line = line.strip()
        m = re.match(r'^(.*?)\s*(?:[x×]\s*(\d+)|\s(\d+))?$', line, re.I)
        if not line or not m or not m.group(1).strip():
            continue
        n = m.group(2) or m.group(3)
        out[m.group(1).strip()] = int(n) if n else None
    return out


def clean(text):
    text = text.lower().replace('1', 'i')          # the shop font's I reads as 1
    for r in ('common', 'uncommon', 'rare', 'epic', 'legendary', 'mythical'):
        text = text.replace(r, '')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z ]', '', text)).strip()


def numeral(raw, base):
    """How many I's follow `base` (OCR reads II as 11, ll or Il), or None."""
    t = raw.lower()
    i = t.rfind(base)
    m = re.match(r'\s*([1il|]{1,3})(?![a-z])', t[i + len(base):]) if i >= 0 else None
    return len(m.group(1)) if m else None


def identify(text, names):
    """The item a slot's text names, or the closest one (0.8+). I, II and III get counted separately."""
    raw, text = text, clean(text)
    if not text:
        return None
    name = _identify(text, names)
    m = re.match(r'^(.*\S)\s+(I{1,3})$', name or '')
    if m:
        n = numeral(raw, m.group(1).split()[-1].lower())
        same = '%s %s' % (m.group(1), 'I' * n) if n else None
        if same in names:
            name = same
    return name


def _identify(text, names):
    best, score = None, 0.0
    for name in sorted(names, key=len, reverse=True):
        c = clean(name)
        if c and c.replace(' ', '') in text.replace(' ', ''):        # OCR is sloppy with spaces
            return name
        c, t = c.replace(' ', ''), text.replace(' ', '')
        # the panel title runs on into a misread rarity ('HeovenlyPotion ILegendory'), so the start counts too
        r = max(difflib.SequenceMatcher(None, c, t).ratio(), difflib.SequenceMatcher(None, c, t[:len(c)]).ratio())
        if r > score:
            best, score = name, r
    return best if score >= 0.8 else None


def reader():
    global _reader
    if _reader is None:
        from rapidocr_onnxruntime import RapidOCR
        try:
            _reader = RapidOCR(intra_op_num_threads=OCR_THREADS, det_intra_op_num_threads=OCR_THREADS,
                               rec_intra_op_num_threads=OCR_THREADS)
        except Exception:
            _reader = RapidOCR()
    return _reader


def read_lines(img):
    if img is None or img.size == 0:
        return []
    result, _ = reader()(np.ascontiguousarray(img[..., ::-1]), use_cls=False)
    return [line[1] for line in result] if result else []


def identify_lines(lines, names):
    """Each line on its own first (rarity or price next to a name throws it off), then all together."""
    for line in lines:
        item = identify(line, names)
        if item:
            return item
    return identify(' '.join(lines), names) if len(lines) > 1 else None


def read_slot(i):
    return read_lines(points.grab('merchantShopItem[%d]' % i))


def nap(seconds, halt):
    end = time.perf_counter() + seconds * game.PACE
    while time.perf_counter() < end:
        if halt():
            return False
        time.sleep(0.02)
    return not halt()


def shut_inventory():
    if not game.close_inventory() and not game.sees_windows():
        points.click('inventoryInvClose', 0.2)              # not recognised at this size, click its X anyway


def use_item(term, halt, say):
    """Search the Inventory for `term` and Use it, only if a result has the item's name colour."""
    what = term.title()
    if game.take_foreground() is None:
        return False
    if not game.open_by_click('inventory', halt):              # retries a swallowed click
        say('the Inventory did not open')
        return False
    if halt() or not points.click('inventoryItemsTab', 0.25):
        return False
    slot = game.search_item(term, say, halt, lambda s: nap(s, halt))
    if slot is None:
        say('no %s used' % what)
        shut_inventory()
        return False
    if halt() or not game.press_point('slot%d' % (slot + 1), 0.2) or not game.press_point('use', 0.3):
        shut_inventory()
        return False
    shut_inventory()
    return True


def teleport(halt, say):
    """Use a Merchant Teleporter, then close the Inventory again (it can pop back up at the merchant)."""
    if not (use_item('merchant teleporter', halt, say) and nap(TELEPORT_S, halt)):
        return False
    points.click('inventoryInvClose', 0.3)
    return not halt()


def open_shop(halt):
    """Talk, pick the green choice, then Leave so the dialogue isn't over the shop. Three tries."""
    for _ in range(3):
        if halt():
            return False
        game.down('e')
        time.sleep(0.05)
        game.up('e')
        if not nap(0.3, halt):
            return False
        for _ in range(3):
            points.click('dialogueSkipDialogue', 0.1)
        if not nap(0.3, halt):
            return False
        at = points.choice('green') if points.dialogue_up() else None     # or a green aura glow would count
        if at is not None:
            game.click(*at, park=False)
            if not settle(halt):
                return False
            return not points.leave_dialogue() or nap(0.3, halt)
    return False


def settle(halt):
    """Wait out the shop's fade-in (two identical grabs in a row)."""
    end, prev = time.perf_counter() + SHOP_SETTLE_S, None
    while time.perf_counter() < end:
        if halt():
            return False
        cur = points.grab('merchantShopProductListRoot')
        if cur is None:
            return False
        if prev is not None and cur.shape == prev.shape and np.array_equal(cur, prev):
            return True
        prev = cur
        time.sleep(0.03)
    return nap(0.1, halt)


def read_shop(names, halt):
    """{slot: item} for what could be read, with a second look at the rest."""
    found = {}
    for attempt in range(2):
        for i in range(1, SLOTS + 1):
            if i in found or halt():
                continue
            try:
                item = identify_lines(read_slot(i), names)
            except Exception:
                item = None
            if item:
                found[i] = item
        if len(found) == SLOTS or not nap(0.3, halt):
            break
    return found


def selected(names):
    """What the detail panel says is picked, i.e. what Purchase would buy."""
    img = points.grab('merchantShopproductDetailPanel')
    if img is None or img.size == 0:
        return None
    return identify_lines(read_lines(img[:max(1, img.shape[0] * 3 // 10)]), names)


def buy(slot, item, amount, names, halt, say=print):
    """Pick the slot, set the amount, Purchase. Checks the panel first, a swallowed click would buy the last pick."""
    if halt() or not points.click('merchantShopItem[%d]' % slot, 0.2):
        return False
    shown = None
    for _ in range(3):
        try:
            shown = selected(names)
        except Exception:
            shown = None
        if shown == item or halt():
            break
        points.click('merchantShopItem[%d]' % slot, 0.3)
    if shown != item:
        say('not buying %s: the shop shows %s picked' % (item, shown or 'something unreadable'))
        return False
    if amount is None:
        points.click('merchantShopSetToMaxButton', 0.15)
    else:
        points.click('merchantShopPurchaseAmountBox', 0.15)
        game.type_term(str(amount))
    if halt():
        return False
    return points.click('merchantShopPurchaseButton', 0.3)


def collect(merchant, wanted, halt, say=print):
    """Teleport, read the shop, buy. Returns ({slot: name}, [bought]), or None if the shop never opened."""
    say('%s arrived: using a Merchant Teleporter' % merchant)
    if not teleport(halt, say):
        return None
    if not open_shop(halt):
        say('%s\'s shop did not open' % merchant)
        return None
    wanted = {(identify(n, KNOWN_ITEMS) or n): a for n, a in wanted.items()}     # 'heavenly potion' -> Heavenly Potion
    names = KNOWN_ITEMS + [n for n in wanted if n not in KNOWN_ITEMS]
    found = read_shop(names, halt)
    say('%s sells: %s' % (merchant, ', '.join('[%d] %s' % kv for kv in sorted(found.items())) or 'nothing read'))
    if not any(item in wanted for item in found.values()):
        say('none of the buy list is here (list: %s)' % (', '.join(wanted) or 'empty'))
    bought = []
    for slot, item in sorted(found.items()):
        if item in wanted and buy(slot, item, wanted[item], names, halt, say):
            bought.append(item if wanted[item] is None else '%s x%d' % (item, wanted[item]))
    return found, bought


def close_shop():
    points.click('merchantShopCloseButton', 0.2)
    time.sleep(0.4)
    points.leave_dialogue(skip=True)                        # the dialogue can outlive the shop
