"""
コーポレートから領収書ファイルアップロード権限が付与された後に実行して、
既存の下書き申請3件に領収書を後付けで添付するスクリプト。

前提:
- 3申請 (18406204, 18406206, 18406208) が既に下書き作成済み
- inputs_202607/entries.json が存在
- freee API に領収書（ファイルボックス）書き込み権限が追加済み

処理:
1. 各申請を GET して現在の purchase_lines を取得
2. 該当エントリの領収書を /api/1/receipts にアップロード
3. 日付＋金額で明細行にマッチさせて receipt_id を紐付ける
4. PUT で申請を更新
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

import requests
from freee_expense.client import FreeeClient

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(HERE, "inputs_202607", "entries.json")

# submit_july_2026.py で作成された3申請とバッチ範囲
BATCHES = [
    (18406204, 0, 30),   # 経費精算申請1/3 → entries[0:30]
    (18406206, 30, 60),  # 経費精算申請2/3 → entries[30:60]
    (18406208, 60, 67),  # 経費精算申請3/3 → entries[60:67]
]


def load_entries() -> list[dict]:
    with open(INPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


def process_app(client: FreeeClient, app_id: int, batch: list[dict]):
    print(f"\n=== 申請 {app_id} ({len(batch)}件) ===")
    company_id = client.get_company_id()

    # 現在の申請を取得
    resp = requests.get(
        f"https://api.freee.co.jp/api/1/expense_applications/{app_id}",
        headers={"Authorization": f"Bearer {client._access_token}"},
        params={"company_id": company_id},
        timeout=30,
    )
    resp.raise_for_status()
    app_data = resp.json()["expense_application"]
    purchase_lines = app_data["purchase_lines"]
    print(f"  現在の明細: {len(purchase_lines)}行")

    # エントリと明細をマッチング → 領収書アップロード → receipt_id を purchase_line に紐付け
    line_receipt_map: dict[int, int] = {}  # purchase_line.id → receipt_id
    for e in batch:
        rp = e.get("receipt_path")
        if not rp:
            continue

        # 日付＋金額でマッチ
        matched = None
        for pl in purchase_lines:
            if pl["transaction_date"] != e["date"]:
                continue
            for eal in pl["expense_application_lines"]:
                if eal["amount"] == int(e["amount"]):
                    matched = pl
                    break
            if matched:
                break

        if not matched:
            print(f"  ⚠ 明細マッチ失敗: {e['date']} ¥{e['amount']} ({rp})")
            continue

        if matched.get("receipt_id"):
            print(f"  skip（既に添付済）: pl={matched['id']}")
            continue

        full = os.path.join(HERE, rp)
        if not os.path.exists(full):
            print(f"  ⚠ ファイル未検出: {rp}")
            continue

        try:
            rid = client.upload_receipt(full)
            line_receipt_map[matched["id"]] = rid
            print(f"  ✓ pl={matched['id']} ← receipt={rid} ({os.path.basename(rp)})")
        except Exception as ex:
            print(f"  ⚠ アップロード失敗 {rp}: {ex}")

    if not line_receipt_map:
        print("  更新不要（新規添付なし）")
        return

    # PUT で申請を更新
    new_purchase_lines = []
    for pl in purchase_lines:
        new_pl = {
            "id": pl["id"],
            "transaction_date": pl["transaction_date"],
            "expense_application_lines": [
                {
                    "id": eal["id"],
                    "description": eal["description"],
                    "amount": eal["amount"],
                    "expense_application_line_template_id": eal["expense_application_line_template_id"],
                }
                for eal in pl["expense_application_lines"]
            ],
        }
        # receipt_id を反映（新規 or 既存）
        if pl["id"] in line_receipt_map:
            new_pl["receipt_id"] = line_receipt_map[pl["id"]]
        elif pl.get("receipt_id"):
            new_pl["receipt_id"] = pl["receipt_id"]
        new_purchase_lines.append(new_pl)

    body = {
        "company_id": company_id,
        "title": app_data["title"],
        "description": app_data["description"],
        "purchase_lines": new_purchase_lines,
    }
    if app_data.get("approval_flow_route_id"):
        body["approval_flow_route_id"] = app_data["approval_flow_route_id"]

    resp = requests.put(
        f"https://api.freee.co.jp/api/1/expense_applications/{app_id}",
        headers={
            "Authorization": f"Bearer {client._access_token}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=60,
    )
    if not resp.ok:
        print(f"  ⚠ PUT 失敗 ({resp.status_code}): {resp.text[:500]}")
    else:
        print(f"  ✓ 申請更新完了（{len(line_receipt_map)} 件の領収書を添付）")


def main():
    entries = load_entries()
    print(f"総エントリ数: {len(entries)}")
    n_with = sum(1 for e in entries if e.get("receipt_path"))
    print(f"領収書あり: {n_with} 件")

    client = FreeeClient()
    for app_id, start, end in BATCHES:
        process_app(client, app_id, entries[start:end])

    print("\n完了。freee で下書きを確認してください。")


if __name__ == "__main__":
    main()
