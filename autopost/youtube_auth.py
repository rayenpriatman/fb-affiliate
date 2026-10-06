"""Dapatkan YT_REFRESH_TOKEN sekali saja, lalu simpan sebagai GitHub secret.

Jalankan di komputer sendiri (butuh browser):
    python -m autopost.youtube_auth --client-id XXX --client-secret YYY

Pakai OAuth client bertipe "Desktop app" dari Google Cloud Console.
"""

from __future__ import annotations

import argparse
import http.server
import os
import secrets
import sys
import urllib.parse
import webbrowser

import requests

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client-id", default=os.environ.get("YT_CLIENT_ID"))
    ap.add_argument("--client-secret", default=os.environ.get("YT_CLIENT_SECRET"))
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    if not args.client_id or not args.client_secret:
        ap.error("isi --client-id dan --client-secret (atau env YT_CLIENT_ID / YT_CLIENT_SECRET)")

    redirect = f"http://127.0.0.1:{args.port}/"
    state = secrets.token_urlsafe(16)
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": args.client_id, "redirect_uri": redirect, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": state,
    })
    result: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            query = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            if "code" not in query and "error" not in query:
                self.send_response(404)
                self.end_headers()
                return
            result.update(query)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("Selesai, kembali ke terminal.".encode())

        def log_message(self, *_):
            pass

    print("Buka URL ini lalu login dengan akun pemilik channel YouTube:\n\n" + url + "\n")
    webbrowser.open(url)
    server = http.server.HTTPServer(("127.0.0.1", args.port), Handler)
    while not result:
        server.handle_request()

    if result.get("state") != state or "code" not in result:
        print(f"Gagal: {result.get('error', 'state tidak cocok')}", file=sys.stderr)
        return 1
    resp = requests.post(TOKEN_URL, data={
        "code": result["code"], "client_id": args.client_id, "client_secret": args.client_secret,
        "redirect_uri": redirect, "grant_type": "authorization_code",
    }, timeout=60)
    body = resp.json()
    if "refresh_token" not in body:
        print(f"Gagal: {body}", file=sys.stderr)
        return 1
    print("YT_REFRESH_TOKEN =\n" + body["refresh_token"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
