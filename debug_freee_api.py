"""
freee API の承認経路・経費申請テンプレート・既存申請を調べて
正しいリクエスト形式を特定するデバッグスクリプト。

出力:
- 承認経路 1469199 の設定内容
- 経費申請テンプレート一覧（明細テンプレート ID を含む）
- 既存の下書き申請の構造（正しい明細フォーマットを確認するため）
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

import requests

TOKEN = os.getenv("FREEE_ACCESS_TOKEN", "")
COMPANY_ID = int(os.getenv("FREEE_COMPANY_ID") or "845775")
BASE = "https://api.freee.co.jp"
H = {"Authorization": f"Bearer {TOKEN}"}


def get(path, **params):
    params.setdefault("company_id", COMPANY_ID)
    r = requests.get(BASE + path, headers=H, params=params, timeout=30)
    print(f"\n=== GET {path} → {r.status_code} ===")
    try:
        data = r.json()
        print(json.dumps(data, ensure_ascii=False, indent=2)[:4000])
        return data
    except Exception:
        print(r.text[:1500])
        return None


def main():
    if not TOKEN:
        print("FREEE_ACCESS_TOKEN が .env にありません。")
        sys.exit(1)

    # 1. 明細テンプレート一覧を色々なURLで試す
    for path in [
        "/api/1/expense_application_line_templates",
        "/api/1/expense_application_lines/templates",
        "/api/1/expense_applications/templates",
    ]:
        get(path)

    # 2. 承認経路一覧
    get("/api/1/approval_flow_routes")


if __name__ == "__main__":
    main()
