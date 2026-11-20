"""Merchant detection: watch rbx-storage.db for a merchant's animation getting used.
Roblox keeps a loaded animation in memory, so we block those files (dummy record, valid checksums) and every visit
shows up, not just the first. The block comes out again when detection stops."""
import glob
import os
import re
import sqlite3
import struct
import threading
import time
from urllib.request import pathname2url

NAMES = ('Mari', 'Jester', 'Rin', 'Boss')
ANIMATION = b'roblox-assettypeid: 24'
_ADDRESS = re.compile(rb'/(?:v\d+/)?sc\d+/([0-9a-f]{32})')
# from MerchantLearner: each merchant's animation address and its file's cache key, same on every PC
ADDRESSES = {'Mari': {'e19e08c3454fe2d8fac8d447434a7c16'},
             'Jester': {'7a41a0002e8294562cd0ac3048386152'},
             'Rin': {'6a3e15a8e4d909486bc445bdb8fe4996'},
             'Boss': {'16daaac736fd49a9bb3782f99f0b29d2', 'b602b26ec2d128fc9e9c869ad18c8cc2'}}
FILES = {'Mari': {'3322c570efc137a477a1e2f04bb39fe7'},
         'Jester': {'1fc3405b9963491cf03fd7b5f89b801b'},
         'Rin': {'25f70ebc3654f26af69047a7d941c859'},
         'Boss': {'741269bab3f96bb43876567e4cd50ac1', 'a8e0b2c3883e429349fa4130714abf8c'}}


LOCAL = os.environ.get('LOCALAPPDATA') or os.path.expanduser(r'~\AppData\Local')


def _changed(path):
    try:
        return max(os.path.getmtime(p) for p in (path, path + '-wal') if os.path.exists(p))
    except (OSError, ValueError):
        return 0


def db_path():
    """This account's rbx-storage.db (normal or Store Roblox), the newest if there are several."""
    found = [os.path.join(LOCAL, 'Roblox', 'rbx-storage.db')]
    store = os.path.join(glob.escape(os.path.join(LOCAL, 'Packages')), 'ROBLOXCORPORATION.ROBLOX*')
    for sub in (('LocalCache', 'Local', 'Roblox'), ('LocalState',)):
        found += glob.glob(os.path.join(store, *sub, 'rbx-storage.db'))
    found = [p for p in found if os.path.isfile(p)]
    return max(found, key=_changed) if found else None


def cache_found():
    return db_path() is not None


def _open(path):
    """Read-only, so it can't write or create a db."""
    return sqlite3.connect('file:%s?mode=ro' % pathname2url(path), uri=True, timeout=2)


def touched(since_ms, path=None):
    """[(address, atime ms)] of animation rows used after since_ms."""
    path = path or db_path()
    if not path or not os.path.exists(path):
        return []
    con = _open(path)
    try:
        # +category makes sqlite use the atime index instead of scanning ~40k rows
        rows = con.execute('SELECT content, atime FROM files WHERE +category = 11 AND atime > ?', (int(since_ms),))
        out = []
        for content, atime in rows:
            if content and ANIMATION in content:
                m = _ADDRESS.search(content)
                if m:
                    out.append((m.group(1).decode(), atime))
        return out
    finally:
        con.close()


_P1, _P2, _P3, _P4, _P5, _M = 0x9E3779B1, 0x85EBCA77, 0xC2B2AE3D, 0x27D4EB2F, 0x165667B1, 0xFFFFFFFF


def _rotl(x, r):
    return ((x << r) | (x >> (32 - r))) & _M


def xxh32(data, seed=0x00C4E564):
    """XXH32 with Roblox's cache seed."""
    n, i = len(data), 0
    if n >= 16:
        v = [(seed + _P1 + _P2) & _M, (seed + _P2) & _M, seed, (seed - _P1) & _M]
        lanes = struct.unpack_from('<%dI' % ((n // 16) * 4), data)
        for j in range(0, len(lanes), 4):
            for k in range(4):
                v[k] = (_rotl((v[k] + lanes[j + k] * _P2) & _M, 13) * _P1) & _M
        i = len(lanes) * 4
        h = (_rotl(v[0], 1) + _rotl(v[1], 7) + _rotl(v[2], 12) + _rotl(v[3], 18)) & _M
    else:
        h = (seed + _P5) & _M
    h = (h + n) & _M
    while i + 4 <= n:
        h = (_rotl((h + struct.unpack_from('<I', data, i)[0] * _P3) & _M, 17) * _P4) & _M
        i += 4
    while i < n:
        h = (_rotl((h + data[i] * _P5) & _M, 11) * _P1) & _M
        i += 1
    h ^= h >> 15
    h = (h * _P2) & _M
    h ^= h >> 13
    h = (h * _P3) & _M
    return h ^ (h >> 16)


def record(body):
    """A cache record the way Roblox writes a download."""
    return (b'RBXH' + struct.pack('<II', 2, 0) + b'\x00'
            + struct.pack('<6I', 200, 0, 0, len(body), xxh32(body) if body else 0, 0) + body)


# valid checksums but not an animation, so it fails to load (an empty one just gets downloaded again)
BLOCKED = record(b'MMacro: this merchant animation is blocked so every visit is seen\n')


def _ids(keys):
    return [bytes.fromhex(k) for k in sorted(keys)]


def reads(keys, path):
    """{key: (last used atime ms, 1 if it holds our block record else 0)}."""
    if not keys or not path or not os.path.exists(path):
        return {}
    con = _open(path)
    try:
        ids = _ids(keys)
        rows = con.execute('SELECT id, atime, content = ? FROM files WHERE id IN (%s)' % ','.join('?' * len(ids)),
                           [BLOCKED] + ids)
        return {k.hex(): (atime, mark) for k, atime, mark in rows}
    finally:
        con.close()


def block(keys, path):
    """Swap these files for the block record. Returns {key: last real read in ms, or None if it wasn't cached}."""
    if not keys or not path or not os.path.exists(path):
        return {}
    now_read = reads(keys, path)
    todo = [k for k in sorted(keys) if now_read.get(k, (0, 0))[1] != 1]
    if not todo:
        return {}
    wrote = {}
    con = sqlite3.connect('file:%s?mode=rw' % pathname2url(path), uri=True, timeout=5)    # never creates one
    try:
        for key in todo:
            k = bytes.fromhex(key)
            # keep its atime, so any later stamp is Roblox reading it
            if con.execute('UPDATE files SET content = ?, size = ? WHERE id = ? AND category = 10',
                           (BLOCKED, len(BLOCKED), k)).rowcount:
                wrote[key] = now_read[key][0] if key in now_read else None
            elif key not in now_read:
                now = int(time.time() * 1000)
                con.execute('INSERT INTO files (id, content, size, hits, atime, category, score, ttl) '
                            'VALUES (?, ?, ?, 0, ?, 10, ?, 0)', (k, BLOCKED, len(BLOCKED), now, now))
                wrote[key] = None
            else:
                continue                # some other kind of row under this key, leave it
            con.commit()
            try:                        # drop the old file on disk, the row holds the content now
                os.remove(os.path.join(os.path.dirname(path), 'rbx-storage', key[:2], key))
            except OSError:
                pass
    finally:
        con.close()
    return wrote


def unblock(keys, path):
    """Remove our block records (Roblox re-downloads the real ones). Returns how many."""
    if not keys or not path or not os.path.exists(path):
        return 0
    con = sqlite3.connect('file:%s?mode=rw' % pathname2url(path), uri=True, timeout=5)
    try:
        ids = _ids(keys)
        n = con.execute('DELETE FROM files WHERE content = ? AND id IN (%s)' % ','.join('?' * len(ids)),
                        [BLOCKED] + ids).rowcount
        con.commit()
        return n
    finally:
        con.close()


class Tracker:
    """Watches the cache for merchants that just came."""

    def __init__(self, path=None, now_ms=None):
        self.path = path                    # None = find it ourselves
        self.found, self.found_at = None, 0.0
        self.since = int(time.time() * 1000) if now_ms is None else now_ms
        self.file_read = {}                 # blocked file key -> when Roblox last read it
        self.ours = set()                   # file keys holding a block record right now
        self.lock = threading.Lock()

    def cache(self):
        if self.path is not None:
            return self.path
        if self.found is None or time.monotonic() - self.found_at > 60 or not os.path.isfile(self.found):
            self.found, self.found_at = db_path(), time.monotonic()
        return self.found

    def forget(self, keys):
        """Just written, so their next stamp is a baseline, not a visit."""
        with self.lock:
            for k in keys:
                self.file_read.pop(k, None)

    def poll(self, known=None, files=None):
        """Merchants seen since the last look, by learned address or by a blocked file read again."""
        path = self.cache()
        rows = touched(self.since, path) if path else []
        known = ADDRESSES if known is None else known
        files = FILES if files is None else files
        read = reads({k for ks in files.values() for k in ks}, path) if path else {}
        came = set()
        with self.lock:
            for address, atime in rows:
                self.since = max(self.since, atime)
                came.update(n for n, addresses in known.items() if address in addresses)
            for key, (atime, _) in read.items():
                if key in self.file_read and atime > self.file_read[key]:
                    came.update(n for n, keys in files.items() if key in keys)
                self.file_read[key] = atime
            self.ours = {k for k, (_, mark) in read.items() if mark}
        return sorted(came)


if __name__ == '__main__':
    import tempfile
    d = tempfile.mkdtemp()
    db = os.path.join(d, 'rbx-storage.db')
    con = sqlite3.connect(db)
    con.execute('CREATE TABLE files (id BLOB PRIMARY KEY NOT NULL, content BLOB, size INTEGER DEFAULT 0 NOT NULL,'
                'hits INTEGER DEFAULT 0 NOT NULL, atime INTEGER DEFAULT 0 NOT NULL, category INTEGER DEFAULT 0 NOT NULL,'
                'score INTEGER DEFAULT 0 NOT NULL, ttl INTEGER DEFAULT 0 NOT NULL)')

    def row(key, address, atime, kind=b'24'):
        content = (b'RBXH\x02\x00\x00\x00\xd6\x02\x00\x00https://fts.rbxcdn.com/v2/sc7/' + address.encode()
                   + b'?encoding=gzip\x00.\x01\x00\x00roblox-assettypeid: ' + kind + b'\r\n')
        con.execute('INSERT OR REPLACE INTO files (id, content, atime, category) VALUES (?, ?, ?, 11)',
                    (key, content, atime))
        con.commit()

    mari, idle, image = 'a' * 32, 'b' * 32, 'c' * 32
    row(b'1', idle, 1000)
    t = Tracker(db, now_ms=500)
    assert t.poll({'Mari': {mari}}, {}) == []
    row(b'2', image, 2000, b'1')                        # not an animation
    row(b'3', mari, 3000)
    row(b'1', idle, 3100)                               # old row used again
    assert t.poll({'Mari': {mari}}, {}) == ['Mari'] and t.poll({'Mari': {mari}}, {}) == []
    con.close()

    # block: existing row replaced, missing one added, every visit seen
    con = sqlite3.connect(db)
    k1, k2 = '3322c570efc137a477a1e2f04bb39fe7', '25f70ebc3654f26af69047a7d941c859'
    con.execute('INSERT INTO files (id, content, size, atime, category) VALUES (?, NULL, 35829, 1000, 10)',
                (bytes.fromhex(k1),))
    con.commit()
    os.makedirs(os.path.join(d, 'rbx-storage', k1[:2]))
    open(os.path.join(d, 'rbx-storage', k1[:2], k1), 'wb').write(b'RBXH real animation')
    files = {'Mari': {k1}, 'Rin': {k2}, 'Jester': set()}
    t = Tracker(db, now_ms=10 ** 13)
    assert t.poll({}, files) == []                                  # baseline
    assert block({k1, k2}, db) == {k1: 1000, k2: None} and block({k1, k2}, db) == {}
    assert not os.path.exists(os.path.join(d, 'rbx-storage', k1[:2], k1))
    assert all(mark == 1 for _, mark in reads({k1, k2}, db).values())
    assert con.execute('SELECT atime, size FROM files WHERE id = ?', (bytes.fromhex(k1),)).fetchone() == (1000, len(BLOCKED))
    t.forget([k1, k2])
    assert t.poll({}, files) == []                                  # blocking isn't a visit
    for visit in range(3):                                          # every visit, not only the first
        con.execute('UPDATE files SET atime = atime + 5000 WHERE id = ?', (bytes.fromhex(k1),))
        con.commit()
        assert t.poll({}, files) == ['Mari'], visit
        assert t.poll({}, files) == []
    assert unblock({k1, k2}, db) == 2 and reads({k1, k2}, db) == {}
    con.close()
    assert block({k1}, os.path.join(d, 'missing.db')) == {} and not os.path.exists(os.path.join(d, 'missing.db'))
    print('merchant cache self check OK')
