"""
freee OAuth2 認証モジュール

初回セットアップ:
  python -m freee_expense.auth

アクセストークンを .env に保存します。
"""
import os
import json
import time
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

import requests
from dotenv import load_dotenv, set_key

load_dotenv()

FREEE_AUTH_URL = "https://accounts.secure.freee.co.jp/public_api/authorize"
FREEE_TOKEN_URL = "https://accounts.secure.freee.co.jp/public_api/token"
REDIRECT_URI = "http://localhost:8080/callback"
ENV_FILE = os.path.join(os.path.dirname(__file__), "..", ".env")

_auth_code: str | None = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            _auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<html><body><h2>認証完了！このタブを閉じてください。</h2></body></html>".encode()
            )
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # サーバーログを抑制


def _run_callback_server() -> HTTPServer:
    server = HTTPServer(("localhost", 8080), _CallbackHandler)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


def get_authorization_url(client_id: str) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
    }
    return FREEE_AUTH_URL + "?" + urllib.parse.urlencode(params)


def exchange_code_for_token(client_id: str, client_secret: str, code: str) -> dict:
    resp = requests.post(
        FREEE_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    resp = requests.post(
        FREEE_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def load_token() -> dict | None:
    """環境変数からトークンを読み込む。有効期限切れなら自動リフレッシュ。"""
    load_dotenv(ENV_FILE)
    access_token = os.getenv("FREEE_ACCESS_TOKEN")
    refresh_token = os.getenv("FREEE_REFRESH_TOKEN")
    expires_at = os.getenv("FREEE_TOKEN_EXPIRES_AT")

    if not access_token or not refresh_token:
        return None

    # 有効期限 60 秒前にリフレッシュ
    if expires_at and float(expires_at) - 60 < time.time():
        client_id = os.getenv("FREEE_CLIENT_ID", "")
        client_secret = os.getenv("FREEE_CLIENT_SECRET", "")
        token = refresh_access_token(client_id, client_secret, refresh_token)
        _save_token(token)
        return token

    return {"access_token": access_token, "refresh_token": refresh_token}


def _save_token(token: dict):
    expires_at = str(time.time() + token.get("expires_in", 21600))
    set_key(ENV_FILE, "FREEE_ACCESS_TOKEN", token["access_token"])
    set_key(ENV_FILE, "FREEE_REFRESH_TOKEN", token["refresh_token"])
    set_key(ENV_FILE, "FREEE_TOKEN_EXPIRES_AT", expires_at)


def run_auth_flow():
    """ブラウザを開いて OAuth2 認証フローを実行し、.env にトークンを保存する。"""
    client_id = os.getenv("FREEE_CLIENT_ID") or input("freee クライアントID: ").strip()
    client_secret = os.getenv("FREEE_CLIENT_SECRET") or input("freee クライアントシークレット: ").strip()

    server = _run_callback_server()
    url = get_authorization_url(client_id)
    print(f"\nブラウザで認証ページを開きます...\n{url}\n")
    webbrowser.open(url)

    print("認証完了を待機中...", end="", flush=True)
    for _ in range(120):
        time.sleep(1)
        if _auth_code:
            break
        print(".", end="", flush=True)
    server.shutdown()

    if not _auth_code:
        raise TimeoutError("認証タイムアウト（2分）。再度実行してください。")

    print("\nアクセストークンを取得中...")
    token = exchange_code_for_token(client_id, client_secret, _auth_code)
    _save_token(token)

    set_key(ENV_FILE, "FREEE_CLIENT_ID", client_id)
    set_key(ENV_FILE, "FREEE_CLIENT_SECRET", client_secret)

    print("認証完了。.env にトークンを保存しました。")
    return token


if __name__ == "__main__":
    run_auth_flow()
