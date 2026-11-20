"""Keep one aura equipped through Aura Storage.
The Equip/Unequip button wins over Roblox's log, which sometimes keeps naming the old aura."""
import difflib
import re
import time

import cv2
import numpy as np

import clipper
import game
import merchant
import points

TRIES = 3               # searches before giving up
EQUIP_WAIT_S = 3.0      # wait for Unequip (or the log) after pressing Equip
CELLS = ['auraStorageAuraCell[1,%d]' % c for c in range(1, 9)] + ['auraStorageAuraCell[2,%d]' % c for c in range(1, 9)]
REGULAR = 'auraStorageAuraRegularTab'
NAME_AREA = ('auraStorageAuraSelectedPreview', 'auraStorageAuraInfoPanel')

norm = clipper.norm


def resolve(text):
    """The aura `text` means: exact, the only one containing it, else the closest. None if nothing's close."""
    want = norm(text)
    if not want:
        return None
    names = clipper.names()
    exact = [n for n in names if norm(n) == want]
    if exact:
        return exact[0]
    inside = [n for n in names if want in norm(n)]
    if len(inside) == 1 and len(want) >= 3:
        return inside[0]
    close = difflib.get_close_matches(want, [norm(n) for n in names], n=1, cutoff=0.8)
    return next(n for n in names if norm(n) == close[0]) if close else None


def search_term(name):
    """What to type in search: the name without symbols if that still matches, else its longest word.
    Cells get read afterwards, so a shared word is fine."""
    for keep in (r'[^\x20-\x7e]+', r'[^A-Za-z0-9 ]+'):
        plain = re.sub(r'\s+', ' ', re.sub(keep, ' ', name)).strip()
        if len(plain) >= 3 and plain.lower() in name.lower():
            return plain
    words = re.findall(r'[A-Za-z0-9]+', name)
    return max(words, key=len) if words else ''


def read(rgb, small=40):
    """OCR lines, upscaled 3x when small (a 768p button is only 18 px tall)."""
    if rgb is None or rgb.size == 0:
        return []
    if rgb.shape[0] < small:
        rgb = cv2.resize(rgb, (rgb.shape[1] * 3, rgb.shape[0] * 3), interpolation=cv2.INTER_CUBIC)
    return merchant.read_lines(rgb)


def button():
    """'equip', 'unequip' or None if unsure. Never press on None, on a worn aura the same button takes it off."""
    rgb = points.grab('auraStorageAuraEquipButton')
    if rgb is None or rgb.size == 0:
        return None
    words, ink = norm(' '.join(read(rgb))), lettering(rgb)
    if 'nequip' in words or 'unequ' in words:
        return 'unequip'
    if re.fullmatch(r'equip', words):
        return None if ink == 'unequip' else 'equip'     # a red "Equip" is a misread Unequip
    return ink


def lettering(rgb):
    """Green text 'equip', red 'unequip', else None."""
    px = rgb.reshape(-1, 3).astype(int)
    lit = px.max(-1)
    text = px[lit > np.median(lit) + 40]                # text is much brighter than the fill
    if len(text) < 0.02 * len(px):
        return None
    r, g, b = text.mean(0)
    if g > r + 40:
        return 'equip'
    if r > g + 40 and r > b + 20:
        return 'unequip'
    return None


def shown():
    """The aura the left panel names, or None."""
    boxes = [points.box(n) for n in NAME_AREA]
    if None in boxes:
        return None
    area = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    lines = read(game.grab(area), small=200)
    keys = {fold(n): n for n in clipper.names() if fold(n)}
    # long names wrap, so try line pairs first or "Rage :" would pass as "Rage"
    tries = [fold(t) for t in [a + b for a, b in zip(lines, lines[1:])] + lines if fold(t)]
    for line in tries:
        if line in keys:
            return keys[line]
    for line in tries:
        close = difflib.get_close_matches(line, list(keys), n=1, cutoff=0.8)
        if close:
            return keys[close[0]]
    return None


def fold(text):
    """norm with o and a merged, OCR reads the game's a as o ("Roge", "Abyssol")."""
    return norm(text).replace('o', 'a')


def nap(seconds, halt):
    end = time.perf_counter() + seconds * game.PACE
    while time.perf_counter() < end:
        if halt():
            return False
        time.sleep(0.02)
    return not halt()


def find(aura, halt, say, skip=()):
    """Search the open Aura Storage, click cells (minus `skip`) until the panel names `aura`. The cell, or None."""
    if halt() or not points.click(REGULAR, 0.2) or not points.click('auraStorageAuraSearchContent', 0.15):
        return None
    game.type_term(search_term(aura))
    if not nap(0.5, halt):
        return None
    for cell in CELLS:                          # copies and variants share a name
        if cell in skip:
            continue
        if halt() or not points.click(cell, 0.2):
            return None
        now = shown()
        if now is not None and norm(now) == norm(aura):
            return cell
    return None


def shut():
    """Close Aura Storage, or click its X anyway (with nothing open that spot is just the world)."""
    if not game.close_inventory():
        points.click('auraStorageAuraCloseButton', 0.2)


def equip(aura, halt, say=print, logged=lambda since: False, other=lambda since: None):
    """Equip `aura` through Aura Storage. True once it's on.
    logged(since): the log says it went on since then. other(since): some other aura that did, or None."""
    if game.take_foreground() is None:
        return False
    wrong = set()                               # cells that turned out to be another aura
    for go in range(1, TRIES + 1):
        if halt():
            return False
        if not game.open_by_click('aura_storage', halt):
            if halt():
                return False
            shut()                              # the side button toggles, so it may be open anyway
            say('Aura Storage did not open (go %d of %d)' % (go, TRIES))
            continue
        cell = find(aura, halt, say, wrong)
        if cell is None:
            shut()
            if halt():
                return False
            say('%s not found in Aura Storage (go %d of %d)' % (aura, go, TRIES))
            continue
        state = button()
        if state == 'unequip':
            say('%s is equipped (its button says Unequip)' % aura)
            shut()
            return True
        if state is None:
            on = logged(0.0)
            say('%s: the Equip button could not be read, so it is not pressed (Roblox\'s log says it is %s; '
                'an odd window shape does this: press F11 for a window MMacro sizes)'
                % (aura, 'equipped' if on else 'not equipped'))
            shut()
            return on
        since = time.time()
        if not points.click('auraStorageAuraEquipButton', 0.1):
            shut()
            return False
        end, how = time.perf_counter() + EQUIP_WAIT_S * game.PACE, None
        while time.perf_counter() < end and not halt():
            if button() == 'unequip':
                how = 'the button now says Unequip'
            elif logged(since):
                how = 'Roblox\'s log says so'
            if how:
                break
            time.sleep(0.2)
        if how and nap(1.0, halt) and other(since):
            say('Roblox\'s log says %s went on instead (a cell read wrong): trying the next one (go %d of %d)'
                % (other(since), go, TRIES))
            wrong.add(cell)
            shut()
            continue
        if how:
            say('%s equipped (%s)' % (aura, how))
            shut()
            return True
        if halt():
            return False
        say('%s not equipped yet: searching again (go %d of %d)' % (aura, go, TRIES))
        shut()
    if not halt():
        say('%s could not be equipped after %d goes' % (aura, TRIES))
    return False
