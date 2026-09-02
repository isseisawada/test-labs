"""
inputs_2026MM/entries_suica.json と entries_receipts.json を統合して
inputs_2026MM/entries.json を生成する。

使い方:
  python3 merge_entries.py --month 8

同時に以下の補正を適用:
- GO タクシー領収書: 日付をファイル名(YYYYMMDD)から抽出
- 年が 20xx 以外に誤読された日付を対象年に補正（Vision 誤読）
- 勘定科目補正（Google Cloud / Apple / note / Staple → 雑費、STATION WORK → 会議費 など）
- 既存の entries.json があれば participants / description / account / date の手修正を引き継ぐ
  （受領書パス receipt_path をキーにマージ）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def fix_receipt(entry: dict, year: int) -> dict:
    """領収書エントリの日付・勘定科目を補正"""
    path = entry.get("receipt_path", "")
    fname = os.path.basename(path)
    vendor = entry.get("vendor", "") or ""

    # 1. GO タクシー: ファイル名から日付を抽出（GO領収書_YYYYMMDD_HHMM.pdf）
    m = re.search(r"GO領収書_(\d{4})(\d{2})(\d{2})", fname)
    if m:
        entry["date"] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # 2. 年の誤読補正（対象年 ±1 以外なら対象年に置換）
    d = str(entry.get("date", ""))
    m = re.match(r"(\d{4})-(\d{2}-\d{2})$", d)
    if m and abs(int(m.group(1)) - year) > 1:
        entry["date"] = f"{year}-{m.group(2)}"

    # 3. 勘定科目補正
    vl = vendor.lower()
    if "google cloud" in vl or "apple" in vl or "note" in vl or "staple" in vl or "soil" in fname.lower():
        entry["account"] = "雑費"
    if "station work" in vl:
        entry["account"] = "会議費"
        if not entry.get("description"):
            entry["description"] = "オフィスブース利用（STATION WORK）"

    entry.setdefault("participants", [])
    return entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", type=int, required=True)
    ap.add_argument("--year", type=int, default=2026)
    args = ap.parse_args()

    base = os.path.join(HERE, f"inputs_{args.year}{args.month:02d}")
    suica_json    = os.path.join(base, "entries_suica.json")
    receipts_json = os.path.join(base, "entries_receipts.json")
    output        = os.path.join(base, "entries.json")

    suica: list[dict] = []
    receipts: list[dict] = []
    if os.path.exists(suica_json):
        with open(suica_json, encoding="utf-8") as f:
            suica = json.load(f)
    else:
        print(f"⚠ {suica_json} なし（Suica 無しとして続行）")
    if os.path.exists(receipts_json):
        with open(receipts_json, encoding="utf-8") as f:
            receipts = json.load(f)
    else:
        print(f"⚠ {receipts_json} なし（領収書無しとして続行）")
    if not suica and not receipts:
        print("エラー: 入力が両方ありません。")
        sys.exit(1)

    receipts = [fix_receipt(e, args.year) for e in receipts]

    # 既存 entries.json の手修正を引き継ぐ（receipt_path キー）
    if os.path.exists(output):
        with open(output, encoding="utf-8") as f:
            prev = {e.get("receipt_path"): e for e in json.load(f) if e.get("receipt_path")}
        carried = 0
        for e in receipts:
            p = prev.get(e.get("receipt_path"))
            if not p:
                continue
            for k in ("participants", "people", "external", "shareholder", "description", "account", "date", "amount"):
                if k in p and p[k] not in (None, "", []):
                    e[k] = p[k]
            carried += 1
        if carried:
            print(f"既存 entries.json から {carried} 件の手修正を引き継ぎました。")

    merged = suica + receipts
    merged.sort(key=lambda e: (e["date"], 0 if e.get("kind") == "suica" else 1))

    total = sum(int(e["amount"]) for e in merged)
    print(f"=== 統合結果: {len(merged)} 件 / ¥{total:,}  (Suica {len(suica)} / 領収書 {len(receipts)}) ===\n")
    for i, e in enumerate(merged, 1):
        if e.get("kind") == "suica":
            route = f"{e.get('from','')} → {e.get('to','')}" if e.get("to") else e.get("from", "")
            desc = f"[Suica] {route}"
        else:
            desc = f"[{e.get('account','?')}] {e.get('vendor','')}"
            if e.get("participants"):
                desc += "  参加者:" + "・".join(e["participants"])
        print(f"  {i:02d}. {e['date']}  {desc}  ¥{int(e['amount']):,}")

    with open(output, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"\n保存: {output}")
    print("→ 会議費・接待交際費の行は entries.json の participants に参加者名（ひらがなフルネーム）を入れてください。")
    print(f"→ 次: python3 submit_expenses.py --month {args.month} --dry-run")


if __name__ == "__main__":
    main()
