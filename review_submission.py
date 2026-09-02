"""
送信内容（entries.json + 判定ロジック）と freee 上の最終状態の差分を出すレビュースクリプト。
UI で手修正した勘定科目・日付・内容を洗い出して、次月のルール改善に使う。

使い方:
  python3 review_submission.py --month 8 --apps 18784480 18784482 18784484
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from dotenv import load_dotenv
load_dotenv(os.path.join(HERE, ".env"), override=True)

import submit_expenses as se
from freee_expense.client import FreeeClient


def fetch_templates(client: FreeeClient) -> dict[int, dict]:
    data = client._get("/api/1/expense_application_line_templates",
                       {"company_id": client.get_company_id(), "limit": 100})
    return {t["id"]: t for t in data.get("expense_application_line_templates", [])}


def fetch_app(client: FreeeClient, app_id: int) -> dict:
    data = client._get(f"/api/1/expense_applications/{app_id}", {"company_id": client.get_company_id()})
    return data["expense_application"]


def sent_lines(month: int, year: int, client: FreeeClient) -> list[dict]:
    """entries.json から、送信時と同じ判定で「送った明細」を再構築"""
    path = os.path.join(HERE, f"inputs_{year}{month:02d}", "entries.json")
    with open(path, encoding="utf-8") as f:
        entries = json.load(f)
    decisions = {id(e): se.decide(e) for e in entries}
    tids = se.resolve_template_ids(client, {d.template_name for d in decisions.values() if d.template_name})
    for d in decisions.values():
        if d.template_name and d.template_name in tids:
            d.tid = tids[d.template_name]
            d.account_override = None
    out = []
    for e in entries:
        d = decisions[id(e)]
        out.append({
            "entry": e,
            "date": e["date"],
            "amount": int(e["amount"]),
            "description": se.build_description(e, d),
            "tid": d.tid,
            "label": d.label,
            "vendor": e.get("vendor") or (f"{e.get('from','')}→{e.get('to','')}" if e.get("kind") == "suica" else ""),
            "kind": e.get("kind", "suica"),
            "used": False,
        })
    return out


def match(sent: list[dict], amount: int, desc: str, date: str) -> dict | None:
    best, best_score = None, -1
    for s in sent:
        if s["used"] or s["amount"] != amount:
            continue
        score = (2 if s["description"] == desc else 0) + (1 if s["date"] == date else 0)
        if score > best_score:
            best, best_score = s, score
    if best:
        best["used"] = True
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", type=int, required=True)
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--apps", type=int, nargs="+", required=True, help="freee 申請ID（複数）")
    args = ap.parse_args()

    client = FreeeClient()
    templates = fetch_templates(client)
    tname = lambda tid: (templates.get(tid, {}).get("name") or f"?{tid}") + f"[{templates.get(tid, {}).get('account_item_name','')}]"

    sent = sent_lines(args.month, args.year, client)
    print(f"送信明細（entries.json）: {len(sent)} 件\n")

    date_changes: list[tuple] = []
    tid_changes: list[tuple] = []
    desc_changes: list[tuple] = []
    unmatched_freee: list[tuple] = []

    for app_id in args.apps:
        app = fetch_app(client, app_id)
        print(f"=== 申請 {app_id}  {app['title']}  status={app['status']}  ¥{app['total_amount']:,}  明細 {len(app['purchase_lines'])} 行 ===")
        for pl in app["purchase_lines"]:
            for eal in pl["expense_application_lines"]:
                f_date, f_amt, f_desc, f_tid = pl["transaction_date"], int(eal["amount"]), eal.get("description") or "", eal.get("expense_application_line_template_id")
                s = match(sent, f_amt, f_desc, f_date)
                if not s:
                    unmatched_freee.append((app_id, f_date, f_amt, f_desc, tname(f_tid)))
                    print(f"  [freee のみ] {f_date} ¥{f_amt:,} {f_desc} → {tname(f_tid)}")
                    continue
                marks = []
                if s["date"] != f_date:
                    date_changes.append((s, f_date)); marks.append(f"日付 {s['date']}→{f_date}")
                if s["tid"] != f_tid:
                    tid_changes.append((s, f_tid)); marks.append(f"科目 {tname(s['tid'])}→{tname(f_tid)}")
                if s["description"] != f_desc:
                    desc_changes.append((s, f_desc)); marks.append(f"内容 「{s['description']}」→「{f_desc}」")
                if marks:
                    print(f"  ✎ ¥{f_amt:,} {s['vendor']}: " + " / ".join(marks))
        print()

    not_sent = [s for s in sent if not s["used"]]
    print("=" * 70)
    print(f"日付変更 {len(date_changes)} 件 / 科目変更 {len(tid_changes)} 件 / 内容変更 {len(desc_changes)} 件 / "
          f"freee にあって送信側に無い {len(unmatched_freee)} 件 / 送信したが freee に無い（削除？） {len(not_sent)} 件")
    for s in not_sent:
        print(f"  [削除?] {s['date']} ¥{s['amount']:,} {s['vendor']} ({s['label']})")

    if tid_changes:
        print("\n--- 次回ルール案（科目）: ベンダー → freee で選び直した経費科目 ---")
        agg = Counter((s["vendor"], s["label"], tname(t)) for s, t in tid_changes)
        for (vendor, old, new), n in agg.most_common():
            print(f"  {vendor}  : {old}  →  {new}  (x{n})")
    if date_changes:
        print("\n--- 日付を直したもの（ファイル名/領収書の日付ルール見直し候補） ---")
        for s, d in date_changes:
            print(f"  {s['vendor']} ¥{s['amount']:,}: {s['date']} → {d}   file={os.path.basename(s['entry'].get('receipt_path',''))}")
    if desc_changes:
        print("\n--- 内容欄を直したもの ---")
        for s, d in desc_changes:
            print(f"  {s['vendor']} ¥{s['amount']:,}: 「{s['description']}」 → 「{d}」")


if __name__ == "__main__":
    main()
