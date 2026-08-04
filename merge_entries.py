"""
inputs_202607/entries_suica.json と entries_receipts.json を統合して
inputs_202607/entries.json を生成する。

同時に以下の補正を適用:
- GO タクシー領収書: 日付をファイル名(YYYYMMDD)から抽出
- 2014-* の日付は 2026-* に補正（Vision 誤読）
- Google Cloud: 通信費 → 雑費
- STATION WORK: 雑費 → 会議費
- Apple / Newspicks / note / Soil work / Staple: 雑費 で確定
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SUICA_JSON    = os.path.join(HERE, "inputs_202607", "entries_suica.json")
RECEIPTS_JSON = os.path.join(HERE, "inputs_202607", "entries_receipts.json")
OUTPUT        = os.path.join(HERE, "inputs_202607", "entries.json")


def fix_receipt_date(entry: dict) -> dict:
    """領収書エントリの日付・勘定科目を補正"""
    path = entry.get("receipt_path", "")
    fname = os.path.basename(path)
    vendor = entry.get("vendor", "")

    # 1. GO タクシー: ファイル名から日付を抽出（GO領収書_YYYYMMDD_HHMM.pdf）
    m = re.search(r"GO領収書_(\d{4})(\d{2})(\d{2})", fname)
    if m:
        entry["date"] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # 2. 誤読された 2014 年 → 2026 年
    if entry["date"].startswith("2014-"):
        entry["date"] = "2026-" + entry["date"][5:]

    # 3. 勘定科目補正
    if "Google Cloud" in vendor:
        entry["account"] = "雑費"
    if "STATION WORK" in vendor or "Station Work" in vendor:
        entry["account"] = "会議費"
    if "Apple" in vendor:
        entry["account"] = "雑費"
    if "note" in vendor.lower():
        entry["account"] = "雑費"
    if "Staple" in vendor or "Soil" in fname:
        entry["account"] = "雑費"

    return entry


def main():
    if not os.path.exists(SUICA_JSON):
        print(f"エラー: {SUICA_JSON} がありません。")
        sys.exit(1)
    if not os.path.exists(RECEIPTS_JSON):
        print(f"エラー: {RECEIPTS_JSON} がありません。")
        sys.exit(1)

    with open(SUICA_JSON, encoding="utf-8") as f:
        suica = json.load(f)
    with open(RECEIPTS_JSON, encoding="utf-8") as f:
        receipts = json.load(f)

    # 領収書に補正を適用
    receipts = [fix_receipt_date(e) for e in receipts]

    # 統合（日付順）
    merged = suica + receipts
    merged.sort(key=lambda e: (e["date"], e.get("kind", "")))

    total = sum(int(e["amount"]) for e in merged)
    print(f"=== 統合結果: {len(merged)} 件 / ¥{total:,} ===\n")
    for i, e in enumerate(merged, 1):
        kind = e.get("kind", "?")
        if kind == "suica":
            route = f"{e.get('from','')} → {e.get('to','')}" if e.get('to') else e.get('from','')
            desc = f"[Suica] {route}"
        else:
            desc = f"[{e.get('account','?')}] {e.get('vendor','')}"
        print(f"  {i:02d}. {e['date']}  {desc}  ¥{int(e['amount']):,}")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"\n保存: {OUTPUT}")
    print("→ 内容を確認したら python3 submit_july_2026.py を実行してください。")


if __name__ == "__main__":
    main()
