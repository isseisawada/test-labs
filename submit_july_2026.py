"""
2026年7月分 経費精算 一括登録スクリプト

使い方:
  1. inputs_202607/entries.json に明細データを書き込む（下記フォーマット）
  2. python3 submit_july_2026.py

entries.json フォーマット:
  [
    {"date": "2026-07-01", "kind": "suica", "from": "逗子", "to": "横浜", "amount": 347},
    {"date": "2026-07-02", "kind": "receipt", "vendor": "スタバ", "amount": 500, "account": "会議費", "receipt_path": "inputs_202607/receipts/stbA.jpg"},
    ...
  ]

出力: 30件ずつのバッチに分けて「経費精算申請1/N」「1/N」... のタイトルで freee に下書き保存。
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from math import ceil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

from freee_expense.client import FreeeClient, ExpenseLine, ExpenseApplication

# 設定 --------------------------------------------------------------------- #
YEAR                    = 2026
MONTH                   = 7
INPUT_FILE              = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "inputs_202607", "entries.json")
DESCRIPTION_PREFIX      = "打ち合わせ"
BATCH_SIZE              = 30
APPROVAL_FLOW_ROUTE_ID  = 1469199  # コーポレートが API 用に発行した承認経路
# 勘定科目名（部分一致で freee 側の候補から選択）
ACCOUNT_TRANSPORT       = "交通費（電車在来線・バス）"
ACCOUNT_TAXI            = "交通費（タクシー等）"
ACCOUNT_MEETING         = "会議費"
ACCOUNT_MISC            = "雑費"
# ------------------------------------------------------------------------- #


def load_entries() -> list[dict]:
    if not os.path.exists(INPUT_FILE):
        print(f"エラー: {INPUT_FILE} がありません。")
        print("先に inputs_202607/entries.json を作成してください。")
        sys.exit(1)
    with open(INPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


def collect_account_names(entries: list[dict]) -> set[str]:
    """entries から必要な勘定科目名を収集"""
    names: set[str] = set()
    for e in entries:
        kind = e.get("kind", "suica")
        if kind == "suica":
            names.add(ACCOUNT_TRANSPORT)
        elif kind == "taxi":
            names.add(ACCOUNT_TAXI)
        elif kind == "receipt":
            names.add(e.get("account", ACCOUNT_MISC))
        else:
            names.add(ACCOUNT_MISC)
    names.add(ACCOUNT_MISC)  # フォールバック用
    return names


def resolve_account_ids(client: FreeeClient, needed: set[str]) -> dict[str, int | None]:
    """必要な勘定科目名 → ID の辞書を返す（見つからなければ None）"""
    result: dict[str, int | None] = {name: None for name in needed}
    try:
        items = client.get_account_items()
        for name in needed:
            # 完全一致優先、なければ双方向部分一致
            best = None
            for item in items:
                if item["name"] == name:
                    best = item
                    break
            if not best:
                for item in items:
                    if name in item["name"] or item["name"] in name:
                        best = item
                        break
            if best:
                result[name] = best["id"]
                print(f"  勘定科目: {name} → ID={best['id']} ({best['name']})")
            else:
                print(f"  ⚠ 勘定科目未解決: {name}（雑費で代替）")
    except Exception as e:
        print(f"  勘定科目の取得スキップ: {e}")
    return result


def entry_to_line(entry: dict, account_ids: dict[str, int | None]) -> ExpenseLine:
    kind = entry.get("kind", "suica")
    d = date.fromisoformat(entry["date"])

    if kind == "suica":
        from_st = entry.get("from", "")
        to_st   = entry.get("to", "")
        route   = f"{from_st} → {to_st}" if to_st else from_st
        return ExpenseLine(
            amount=int(entry["amount"]),
            description=f"{DESCRIPTION_PREFIX}（{route}）",
            expense_date=d,
            account_item_id=account_ids.get(ACCOUNT_TRANSPORT),
        )

    if kind == "taxi":
        return ExpenseLine(
            amount=int(entry["amount"]),
            description=entry.get("description", "タクシー"),
            expense_date=d,
            account_item_id=account_ids.get(ACCOUNT_TAXI) or account_ids.get(ACCOUNT_TRANSPORT),
        )

    if kind == "receipt":
        acct_name = entry.get("account", ACCOUNT_MISC)
        return ExpenseLine(
            amount=int(entry["amount"]),
            description=entry.get("description", entry.get("vendor", "領収書")),
            expense_date=d,
            account_item_id=account_ids.get(acct_name) or account_ids.get(ACCOUNT_MISC),
        )

    # デフォルト
    return ExpenseLine(
        amount=int(entry["amount"]),
        description=entry.get("description", ""),
        expense_date=d,
        account_item_id=account_ids.get(ACCOUNT_MISC),
    )


def main():
    entries = load_entries()
    if not entries:
        print("明細が空です。")
        sys.exit(1)

    total = sum(int(e["amount"]) for e in entries)
    num_batches = ceil(len(entries) / BATCH_SIZE)
    print(f"=== 2026年{MONTH}月分 経費精算 ===")
    print(f"総件数: {len(entries)} 件 / ¥{total:,}")
    print(f"バッチ: {BATCH_SIZE} 件 × {num_batches} 申請\n")

    client = FreeeClient()
    needed = collect_account_names(entries)
    account_ids = resolve_account_ids(client, needed)

    for batch_idx in range(num_batches):
        start = batch_idx * BATCH_SIZE
        end   = min(start + BATCH_SIZE, len(entries))
        batch = entries[start:end]
        title = f"経費精算申請{batch_idx + 1}/{num_batches}"
        batch_total = sum(int(e["amount"]) for e in batch)

        print(f"\n--- {title} ({len(batch)}件 / ¥{batch_total:,}) ---")
        lines = [entry_to_line(e, account_ids) for e in batch]
        for e, ln in zip(batch, lines):
            print(f"  {ln.expense_date}  {ln.description}  ¥{ln.amount:,}")

        application = ExpenseApplication(
            title=title,
            lines=lines,
            description=f"2026年{MONTH}月分 経費精算 {len(lines)}件 合計¥{batch_total:,}",
            approval_flow_route_id=APPROVAL_FLOW_ROUTE_ID,
        )
        result = client.create_expense_application(application)
        print(f"  → 申請ID: {result['id']}")


if __name__ == "__main__":
    main()
