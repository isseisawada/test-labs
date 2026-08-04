"""
2026年7月分 経費精算 一括登録スクリプト（新API形式・明細テンプレート対応）

使い方:
  1. inputs_202607/entries.json に明細データを配置
  2. python3 submit_july_2026.py --dry-run  # プレビュー
  3. python3 submit_july_2026.py             # freee に登録

30 件ずつのバッチに分けて「経費精算申請 X/N」タイトルで freee に下書き保存。
承認経路: 1469199（コーポレートが API 用に発行）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from math import ceil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

from freee_expense.client import FreeeClient, ExpenseLine, ExpenseApplication

# ------------------------------------------------------------------------- #
# 設定
# ------------------------------------------------------------------------- #
YEAR                    = 2026
MONTH                   = 7
INPUT_FILE              = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "inputs_202607", "entries.json")
BATCH_SIZE              = 30
APPROVAL_FLOW_ROUTE_ID  = 1469199

# 明細テンプレート ID（freee 側で定義されているもの）
T_SUICA        = 289807  # 交通費（電車在来線・バス）
T_SHINKANSEN   = 300519  # 交通費（特急・新幹線）
T_TAXI         = 300520  # 交通費（タクシー）
T_GAS          = 300524  # ガソリン代
T_PARKING      = 300525  # 駐車場代
T_MEETING_IN   = 300528  # 会議費（社内）
T_MEETING_EXT  = 300529  # 会議費（社外）
T_ENT_LOW      = 300530  # 接待交際費（一人5000円以下）
T_ENT_HIGH     = 300531  # 接待交際費（一人5000円超）
T_SUPPLY       = 300535  # 備品消耗品（事務用品等）→ サブスク等の雑費フォールバック
# ------------------------------------------------------------------------- #


def load_entries() -> list[dict]:
    if not os.path.exists(INPUT_FILE):
        print(f"エラー: {INPUT_FILE} がありません。")
        sys.exit(1)
    with open(INPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


def pick_template(entry: dict) -> tuple[int, str]:
    """エントリから明細テンプレート ID と表示名を決定"""
    kind = entry.get("kind", "suica")
    vendor = entry.get("vendor", "") or ""
    account = entry.get("account", "") or ""
    amount = int(entry.get("amount", 0))
    description = entry.get("description", "") or ""

    # Suica → 電車バス（バス含む）
    if kind == "suica":
        return T_SUICA, "電車・バス"

    # 種別が taxi
    if kind == "taxi":
        return T_TAXI, "タクシー"

    # 領収書：ベンダー別に振り分け
    v = vendor
    if "GO株式会社" in v or v.startswith("GO"):
        return T_TAXI, "タクシー"
    if "東日本旅客" in v or "JR" in v.upper() or "新幹線" in v:
        return T_SHINKANSEN, "特急・新幹線"
    if "石油" in v or "ガソリン" in v or "SS" in v:
        return T_GAS, "ガソリン代"
    if any(k in v for k in ["パーク", "駐車場", "パーキング", "アイペック", "ナビパーク"]):
        return T_PARKING, "駐車場代"

    # 勘定科目名 or 金額でざっくり判定
    # 接待交際費: 一人¥10,000 で分ける（澤田＋参加者数の情報がないので合計金額の目安で判定）
    # ¥30,000 以上 → 高額なので 10,000超 と推定、それ未満 → 10,000以下
    # 実運用では freee UI で個別に人数見て確認する前提
    if account == "接待交際費":
        return (T_ENT_HIGH, "接待交際費(10000超)") if amount >= 30000 else (T_ENT_LOW, "接待交際費(10000以下)")

    if account == "会議費" or "STATION WORK" in v or "Station Work" in v:
        return T_MEETING_IN, "会議費(社内)"

    # 上記に該当しない領収書は消耗品にフォールバック（Google Cloud, Apple, note, Soil work 等）
    return T_SUPPLY, "備品消耗品(事務用品等)"


def entry_to_line(entry: dict, receipt_id: int | None = None) -> tuple[ExpenseLine, str]:
    d = date.fromisoformat(entry["date"])
    tid, label = pick_template(entry)
    kind = entry.get("kind", "suica")

    if kind == "suica":
        from_st = entry.get("from", "")
        to_st   = entry.get("to", "")
        route   = f"{from_st} → {to_st}" if to_st else from_st
        description = f"打ち合わせ（{route}）"
    else:
        description = entry.get("description") or f"{entry.get('vendor','')}"

    return (ExpenseLine(
        amount=int(entry["amount"]),
        description=description,
        expense_date=d,
        line_template_id=tid,
        receipt_ids=[receipt_id] if receipt_id else [],
    ), label)


def upload_all_receipts(client: FreeeClient, entries: list[dict]) -> dict[str, int]:
    """entries 内で参照される全領収書ファイルを一度だけアップロードし path→id を返す"""
    here = os.path.dirname(os.path.abspath(__file__))
    cache: dict[str, int] = {}
    paths = []
    for e in entries:
        p = e.get("receipt_path")
        if p and p not in cache and p not in paths:
            paths.append(p)

    if not paths:
        return cache

    print(f"領収書アップロード中（{len(paths)} 件）...")
    for p in paths:
        full = os.path.join(here, p)
        if not os.path.exists(full):
            print(f"  ⚠ ファイル未検出: {p}")
            continue
        try:
            rid = client.upload_receipt(full)
            cache[p] = rid
        except Exception as e:
            print(f"  ⚠ アップロード失敗 {p}: {e}")
    print()
    return cache


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="freee に送信せずプレビューのみ")
    args = parser.parse_args()

    entries = load_entries()
    if not entries:
        print("明細が空です。")
        sys.exit(1)

    total = sum(int(e["amount"]) for e in entries)
    num_batches = ceil(len(entries) / BATCH_SIZE)
    n_with_receipt = sum(1 for e in entries if e.get("receipt_path"))
    print(f"=== 2026年{MONTH}月分 経費精算 ===")
    print(f"総件数: {len(entries)} 件 / ¥{total:,}")
    print(f"領収書あり: {n_with_receipt} 件")
    print(f"バッチ: {BATCH_SIZE} 件 × {num_batches} 申請")
    if args.dry_run:
        print("モード: ドライラン（freee には送信・アップロードしません）")
    print()

    # 領収書アップロード（実行モードのみ）
    client = None
    receipt_id_by_path: dict[str, int] = {}
    if not args.dry_run:
        client = FreeeClient()
        receipt_id_by_path = upload_all_receipts(client, entries)

    for batch_idx in range(num_batches):
        start = batch_idx * BATCH_SIZE
        end   = min(start + BATCH_SIZE, len(entries))
        batch = entries[start:end]
        title = f"経費精算申請{batch_idx + 1}/{num_batches}"
        batch_total = sum(int(e["amount"]) for e in batch)

        print(f"--- {title} ({len(batch)}件 / ¥{batch_total:,}) ---")
        lines_and_labels = []
        for e in batch:
            rid = receipt_id_by_path.get(e.get("receipt_path", ""))
            lines_and_labels.append(entry_to_line(e, rid))

        for e, (ln, label) in zip(batch, lines_and_labels):
            rcpt_mark = " 📎" if ln.receipt_ids else (" 📎(要UP)" if e.get("receipt_path") else "")
            print(f"  {ln.expense_date}  [{label}]  {ln.description}  ¥{ln.amount:,}{rcpt_mark}")
        print()

        if args.dry_run:
            continue

        application = ExpenseApplication(
            title=title,
            lines=[ln for ln, _ in lines_and_labels],
            description=f"2026年{MONTH}月分 経費精算 {len(batch)}件 合計¥{batch_total:,}",
            approval_flow_route_id=APPROVAL_FLOW_ROUTE_ID,
        )
        result = client.create_expense_application(application)
        print(f"  → 申請ID: {result['id']}\n")


if __name__ == "__main__":
    main()
