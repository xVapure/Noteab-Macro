import glob
import os
import re
import sqlite3
import struct
import threading
import time
from urllib.request import pathname2url

NAMES = ('Mari', 'Jester', 'Rin')
ANIMATION = b'roblox-assettypeid: 24'
_ADDRESS = re.compile(rb'/(?:v\d+/)?sc\d+/([0-9a-f]{32})')
ADDRESSES = {'Mari': {'e19e08c3454fe2d8fac8d447434a7c16'},
             'Jester': {'7a41a0002e8294562cd0ac3048386152'},
             'Rin': {'6a3e15a8e4d909486bc445bdb8fe4996'}}
FILES = {'Mari': {'3322c570efc137a477a1e2f04bb39fe7'},
         'Jester': {'1fc3405b9963491cf03fd7b5f89b801b'},
         'Rin': {'25f70ebc3654f26af69047a7d941c859'}}
LOCAL = os.environ.get('LOCALAPPDATA') or os.path.expanduser(r'~\AppData\Local')
_P1, _P2, _P3, _P4, _P5, _MASK = 0x9E3779B1, 0x85EBCA77, 0xC2B2AE3D, 0x27D4EB2F, 0x165667B1, 0xFFFFFFFF


def _changed(path):
    try:
        return max(os.path.getmtime(p) for p in (path, path + '-wal') if os.path.exists(p))
    except (OSError, ValueError):
        return 0


def db_path():
    found = [os.path.join(LOCAL, 'Roblox', 'rbx-storage.db')]
    store = os.path.join(glob.escape(os.path.join(LOCAL, 'Packages')), 'ROBLOXCORPORATION.ROBLOX*')
    for sub in (('LocalCache', 'Local', 'Roblox'), ('LocalState',)):
        found.extend(glob.glob(os.path.join(store, *sub, 'rbx-storage.db')))
    found = [path for path in found if os.path.isfile(path)]
    return max(found, key=_changed) if found else None


def cache_found():
    return db_path() is not None


def _open(path, mode='ro'):
    return sqlite3.connect('file:%s?mode=%s' % (pathname2url(path), mode), uri=True, timeout=5)


def touched(since_ms, path=None):
    path = path or db_path()
    if not path or not os.path.exists(path):
        return []
    con = _open(path)
    try:
        rows = con.execute('SELECT content, atime FROM files WHERE +category = 11 AND atime > ?', (int(since_ms),))
        out = []
        for content, atime in rows:
            if content and ANIMATION in content:
                match = _ADDRESS.search(content)
                if match:
                    out.append((match.group(1).decode(), atime))
        return out
    finally:
        con.close()


def _rotl(value, bits):
    return ((value << bits) | (value >> (32 - bits))) & _MASK


def xxh32(data, seed=0x00C4E564):
    size, index = len(data), 0
    if size >= 16:
        values = [(seed + _P1 + _P2) & _MASK, (seed + _P2) & _MASK, seed, (seed - _P1) & _MASK]
        lanes = struct.unpack_from('<%dI' % ((size // 16) * 4), data)
        for offset in range(0, len(lanes), 4):
            for lane in range(4):
                values[lane] = (_rotl((values[lane] + lanes[offset + lane] * _P2) & _MASK, 13) * _P1) & _MASK
        index = len(lanes) * 4
        result = (_rotl(values[0], 1) + _rotl(values[1], 7) + _rotl(values[2], 12) + _rotl(values[3], 18)) & _MASK
    else:
        result = (seed + _P5) & _MASK
    result = (result + size) & _MASK
    while index + 4 <= size:
        result = (_rotl((result + struct.unpack_from('<I', data, index)[0] * _P3) & _MASK, 17) * _P4) & _MASK
        index += 4
    while index < size:
        result = (_rotl((result + data[index] * _P5) & _MASK, 11) * _P1) & _MASK
        index += 1
    result ^= result >> 15
    result = (result * _P2) & _MASK
    result ^= result >> 13
    result = (result * _P3) & _MASK
    return result ^ (result >> 16)


def record(body):
    return (b'RBXH' + struct.pack('<II', 2, 0) + b'\x00'
            + struct.pack('<6I', 200, 0, 0, len(body), xxh32(body) if body else 0, 0) + body)


BLOCKED = record(b'Coteab: merchant animation blocked for repeat detection\n')


def reads(keys, path):
    if not keys or not path or not os.path.exists(path):
        return {}
    con = _open(path)
    try:
        ids = [bytes.fromhex(key) for key in sorted(keys)]
        rows = con.execute('SELECT id, atime, content = ? FROM files WHERE id IN (%s)' % ','.join('?' * len(ids)),
                           [BLOCKED] + ids)
        return {key.hex(): (atime, marked) for key, atime, marked in rows}
    finally:
        con.close()


def block(keys, path):
    if not keys or not path or not os.path.exists(path):
        return {}
    current = reads(keys, path)
    pending = [key for key in sorted(keys) if current.get(key, (0, 0))[1] != 1]
    if not pending:
        return {}
    written = {}
    con = sqlite3.connect('file:%s?mode=rw' % pathname2url(path), uri=True, timeout=5)
    try:
        for key in pending:
            item = bytes.fromhex(key)
            if con.execute('UPDATE files SET content = ?, size = ? WHERE id = ? AND category = 10',
                           (BLOCKED, len(BLOCKED), item)).rowcount:
                written[key] = current[key][0] if key in current else None
            elif key not in current:
                now = int(time.time() * 1000)
                con.execute('INSERT INTO files (id, content, size, hits, atime, category, score, ttl) '
                            'VALUES (?, ?, ?, 0, ?, 10, ?, 0)', (item, BLOCKED, len(BLOCKED), now, now))
                written[key] = None
            else:
                continue
            con.commit()
            try:
                os.remove(os.path.join(os.path.dirname(path), 'rbx-storage', key[:2], key))
            except OSError:
                pass
    finally:
        con.close()
    return written


def unblock(keys, path):
    if not keys or not path or not os.path.exists(path):
        return 0
    con = sqlite3.connect('file:%s?mode=rw' % pathname2url(path), uri=True, timeout=5)
    try:
        ids = [bytes.fromhex(key) for key in sorted(keys)]
        query = 'DELETE FROM files WHERE content = ? AND id IN (%s)' % ','.join('?' * len(ids))
        count = con.execute(query, [BLOCKED] + ids).rowcount
        con.commit()
        return count
    finally:
        con.close()


class Tracker:
    def __init__(self, path=None, now_ms=None):
        self.path = path
        self.found = None
        self.found_at = 0.0
        self.since = int(time.time() * 1000) if now_ms is None else now_ms
        self.file_read = {}
        self.ours = set()
        self.lock = threading.Lock()

    def cache(self):
        if self.path is not None:
            return self.path
        if self.found is None or time.monotonic() - self.found_at > 60 or not os.path.isfile(self.found):
            self.found, self.found_at = db_path(), time.monotonic()
        return self.found

    def forget(self, keys):
        with self.lock:
            for key in keys:
                self.file_read.pop(key, None)

    def poll(self, known=None, files=None):
        path = self.cache()
        rows = touched(self.since, path) if path else []
        known = ADDRESSES if known is None else known
        files = FILES if files is None else files
        keys = {key for values in files.values() for key in values}
        read = reads(keys, path) if path else {}
        came = set()
        with self.lock:
            for address, atime in rows:
                self.since = max(self.since, atime)
                came.update(name for name, addresses in known.items() if address in addresses)
            for key, (atime, marked) in read.items():
                if key in self.file_read and atime > self.file_read[key]:
                    came.update(name for name, file_keys in files.items() if key in file_keys)
                self.file_read[key] = atime
            self.ours = {key for key, (_, marked) in read.items() if marked}
        return sorted(came)
