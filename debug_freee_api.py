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
        # 全文出力
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return data
    except Exception:
        print(r.text)
        return None


def main():
    if not TOKEN:
        print("FREEE_ACCESS_TOKEN が .env にありません。")
        sys.exit(1)

    # 明細テンプレート一覧を全件取得（id/name のみ抽出して簡潔に）
    data = get("/api/1/expense_application_line_templates")
    if data:
        print("\n" + "=" * 60)
        print("【テンプレート一覧サマリ】")
        for t in data.get("expense_application_line_templates", []):
            print(f"  id={t['id']:>6}  {t['name']}  [{t['account_item_name']}]")


if __name__ == "__main__":
    main()
