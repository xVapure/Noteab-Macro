"""Eden: spotting it, walking to it, and the contract."""
import os
import sys
import time

import cv2
import numpy as np

import game

HERE = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
POINTS = (('contract', 'Eden: Contract button'),)
SHOWS = 0.75             # match score for Eden
SIGNED = 0.8             # match score for the contract
SAME = 0.98              # screen this close to the last one isn't searched again
LOOK_EVERY_S = 3.0       # a search costs ~0.6 core-seconds and Eden stays for minutes
SCALES = np.linspace(0.5, 1.5, 20)
SETTLE_S = 25.0          # wait after Eden shows, before walking
TALK_S = 5.0             # after E, before the Contract button
CONTRACT_S = 50.0        # longest to wait for the signed contract
COOLDOWN_S = 60.0        # after Eden, before looking again
RECORD_S = 60
# Portable Crack spawn -> Eden, camera squared by Collection first
PATH = [(0, 'down', 's'), (0.17, 'up', 's'), (0.22, 'down', 's'), (0.22, 'down', 'd'), (2.57, 'up', 'd'),
        (4.37, 'up', 's'), (4.42, 'down', 'd'), (4.87, 'up', 'd'), (4.92, 'down', 'd'), (4.92, 'down', 'w'),
        (7.92, 'up', 'w'), (8.12, 'down', 'w'), (9.12, 'up', 'w'), (9.32, 'down', 'w'), (10.32, 'up', 'w'),
        (10.47, 'down', 'w'), (12.47, 'up', 'w'), (12.47, 'up', 'd'), (12.52, 'down', 's'), (12.82, 'down', 'd'),
        (12.97, 'up', 'd'), (14.02, 'down', ' '), (14.82, 'up', ' '), (20.17, 'up', 's')]


def _template(name):
    """Through numpy because cv2.imread chokes on non-ASCII usernames in the path."""
    return cv2.imdecode(np.fromfile(os.path.join(HERE, name), np.uint8), cv2.IMREAD_GRAYSCALE)


def _client():
    return cv2.cvtColor(np.ascontiguousarray(game.grab(game.client_box((0.0, 0.0, 1.0, 1.0)))), cv2.COLOR_RGB2GRAY)


def best_score(gray, template, scales=SCALES):
    best = -1.0
    for scale in scales:
        t = cv2.resize(template, None, fx=scale, fy=scale)
        if t.shape[0] > gray.shape[0] or t.shape[1] > gray.shape[1]:
            continue
        best = max(best, cv2.minMaxLoc(cv2.matchTemplate(gray, t, cv2.TM_CCOEFF_NORMED))[1])
    return best


class Watcher:
    """Watches for Eden, skipping screens that haven't changed."""

    def __init__(self):
        self.eden = _template('eden.png')
        self.last = None
        self.looked = 0.0

    def seen(self):
        if time.monotonic() - self.looked < LOOK_EVERY_S:
            return False
        self.looked = time.monotonic()
        gray = _client()
        small = cv2.resize(gray, (64, 64))
        if self.last is not None and cv2.matchTemplate(small, self.last, cv2.TM_CCOEFF_NORMED)[0][0] >= SAME:
            return False
        self.last = small
        return best_score(gray, self.eden) >= SHOWS


def signed(stop, timeout=CONTRACT_S):
    contract = _template('contract.png')
    end = time.time() + timeout
    while time.time() < end and not stop():
        if best_score(_client(), contract, (1.0,)) >= SIGNED:
            return True
        time.sleep(0.5)
    return False


def tilt():
    """Drag the camera down 250 px, same as when the path was recorded."""
    game.glide(*game.client_box((0.5, 0.4, 0.5, 0.4))[:2])
    time.sleep(0.05)
    game.button('right', True)
    for _ in range(5):
        game._mouse(0x0001, dy=50)
        time.sleep(0.01)
    game.button('right', False)
    time.sleep(0.5)


def walk(stop):
    import fishing
    try:
        fishing.walk(PATH, stop)
    finally:
        game.release_all()


def record(seconds, stop):
    """Record the client to an .avi in the app folder. Never raises."""
    try:
        os.makedirs(game.APP_DIR, exist_ok=True)
        path = os.path.join(game.APP_DIR, time.strftime('eden_%Y%m%d_%H%M%S.avi'))
        frame = game.grab(game.client_box((0.0, 0.0, 1.0, 1.0)))
        h, w = frame.shape[:2]
        out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'XVID'), 20.0, (w, h))
        end = time.time() + seconds
        while time.time() < end and not stop():
            frame = game.grab(game.client_box((0.0, 0.0, 1.0, 1.0)))
            if frame.shape[:2] == (h, w):
                out.write(cv2.cvtColor(np.ascontiguousarray(frame), cv2.COLOR_RGB2BGR))
            time.sleep(1 / 20.0)
        out.release()
    except Exception:
        pass


if __name__ == '__main__':
    eden, contract = _template('eden.png'), _template('contract.png')
    assert eden is not None and contract is not None, 'eden.png or contract.png missing'
    screen = np.zeros((1080, 1920), np.uint8)
    screen[200:200 + eden.shape[0], 300:300 + eden.shape[1]] = eden
    assert best_score(screen, eden) >= SHOWS, 'Eden drawn on screen was not found'
    assert best_score(np.zeros((1080, 1920), np.uint8), eden) < SHOWS, 'a black screen read as Eden'
    keys = {key for _, _, key in PATH}
    assert keys <= set(game.VK), 'path keys game.down cannot press: %s' % (keys - set(game.VK))
    held = set()
    for _, how, key in PATH:
        (held.add if how == 'down' else held.discard)(key)
    assert not held and PATH == sorted(PATH, key=lambda e: e[0]), 'PATH leaves a key held or goes back in time'
    print('eden self check: Eden found when drawn, not on black; every path key can be pressed')
