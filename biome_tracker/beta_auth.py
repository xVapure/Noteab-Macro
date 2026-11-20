import os, sys, json, time, hmac, hashlib, threading, webbrowser, urllib.request as ur, urllib.parse as up, ssl, subprocess, ctypes
from http.server import HTTPServer, BaseHTTPRequestHandler

CLIENT_ID, REDIRECT_PORT = "1508131861338001572", 48721
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
OAUTH2_URL = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={up.quote(REDIRECT_URI)}&response_type=code&scope=identify"

_ks = lambda: bytes([67, 111, 116, 101, 97, 98, 66, 69, 84, 65, 84, 85, 70, 70, 70, 70, 70]).decode()
_ba = lambda: bytes([104, 116, 116, 112, 58, 47, 47, 51, 56, 46, 56, 51, 46, 49, 51, 56, 46, 53, 57, 58, 50, 53, 56, 52, 54]).decode()
_ssl_ctx = ssl.create_default_context()
_auth_code_result = {"code": None, "error": None}

def _verify_code_via_backend(code):
    if not _ba(): return None, None, False
    payload = json.dumps({"code": code, "redirect_uri": REDIRECT_URI, "ts": int(time.time())}).encode("utf-8")
    sig = hmac.new(_ks().encode(), payload, hashlib.sha256).hexdigest()
    try:
        with ur.urlopen(ur.Request(f"{_ba()}/verify", data=payload, headers={"Content-Type": "application/json", "X-Signature": sig}, method="POST"), timeout=30, context=_ssl_ctx) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if abs(int(time.time()) - res.get("ts", 0)) > 86400: return None, None, False
            exp_sig = hmac.new(_ks().encode(), f"{res.get('user_id', '')}:{res.get('allowed', False)}:{res.get('ts', 0)}".encode(), hashlib.sha256).hexdigest()
            return (res.get("user_id", ""), res.get("username", "Unknown"), bool(res.get("allowed", False))) if hmac.compare_digest(res.get("sig", ""), exp_sig) else (None, None, False)
    except Exception as e: print(f"[BetaAuth] Verify Error: {e}"); return None, None, False

def _recheck_via_backend(user_id):
    if not _ba(): return False
    payload = json.dumps({"user_id": user_id, "ts": int(time.time())}).encode("utf-8")
    sig = hmac.new(_ks().encode(), payload, hashlib.sha256).hexdigest()
    try:
        with ur.urlopen(ur.Request(f"{_ba()}/recheck", data=payload, headers={"Content-Type": "application/json", "X-Signature": sig}, method="POST"), timeout=30, context=_ssl_ctx) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if abs(int(time.time()) - res.get("ts", 0)) > 86400: return False
            exp_sig = hmac.new(_ks().encode(), f"{user_id}:{res.get('allowed', False)}:{res.get('ts', 0)}".encode(), hashlib.sha256).hexdigest()
            return bool(res.get("allowed", False)) if hmac.compare_digest(res.get("sig", ""), exp_sig) else False
    except Exception as e: print(f"[BetaAuth] Recheck Error: {e}"); return False

class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = up.parse_qs(up.urlparse(self.path).query)
        if "code" in params:
            _auth_code_result["code"] = params["code"][0]
            self._send_html("<h2 style='color:#43b581;font-family:sans-serif;text-align:center;margin-top:80px;'>Discord Login Successful!</h2><p style='color:#b9bbbe;font-family:sans-serif;text-align:center;'>You can close this tab and return to the macro to check your beta access status.</p>")
        else:
            _auth_code_result["error"] = params.get("error", ["unknown"])[0]
            self._send_html(f"<h2 style='color:#f04747;font-family:sans-serif;text-align:center;margin-top:80px;'>Authorization failed: {_auth_code_result['error']}</h2>")
    def _send_html(self, body):
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(f"<html><body>{body}</body></html>".encode("utf-8"))
    def log_message(self, *args): pass

def _run_oauth_flow(timeout=120):
    _auth_code_result.update({"code": None, "error": None})
    server = HTTPServer(("127.0.0.1", REDIRECT_PORT), _OAuthCallbackHandler)
    webbrowser.open(OAUTH2_URL)
    deadline = time.time() + timeout
    while time.time() < deadline and not (_auth_code_result["code"] or _auth_code_result["error"]):
        server.timeout = max(1, deadline - time.time()); server.handle_request()
    server.server_close()
    return _auth_code_result["code"]

_verified_user_id, _verified_username, _auth_ticket = None, None, None
_derive_ticket = lambda uid: hmac.new(_ks().encode(), f"beta:{uid}:{int(time.time()) // 3600}".encode(), hashlib.sha256).hexdigest()[:16]

def is_verified():
    return bool(_verified_user_id)

def verify_access():
    global _verified_user_id, _verified_username, _auth_ticket

    if not (CLIENT_ID and _ba() and _ks()): return True
    code = _run_oauth_flow()
    if not code: return False
    uid, uname, allowed = _verify_code_via_backend(code)
    if allowed and uid: _verified_user_id, _verified_username, _auth_ticket = uid, uname, _derive_ticket(uid); return True
    return False

def show_auth_popup():
    if ctypes.windll.user32.MessageBoxW(0, "This is a beta version of Coteab Macro.\n\nYou need to verify your Discord account to continue.\nClick 'Yes' to open Discord login in your browser.\n\nMake sure you are in the Coteab Discord server\nand have the beta access role!!!!!!", "Coteab Macro \u2014 Beta Access", 0x44) != 6:
        ctypes.windll.user32.MessageBoxW(0, "Authentication cancelled.\nThe macro will now close.", "Coteab Macro", 0x40); return False
    if not verify_access():
        ctypes.windll.user32.MessageBoxW(0, "You do not have beta access.\n\nMake sure you:\n\u2022 Are in the Coteab Discord server\n\u2022 Have the beta access role!!!!!!\n\nJoin: https://discord.gg/coteab", "Coteab Macro \u2014 Access Denied", 0x10); return False
    return True
