"""
2026年4月分 Suica 交通費 一括登録スクリプト
申請タイトル: 経費精算申請1/3
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date
from dotenv import load_dotenv
# スクリプトと同じディレクトリの .env を確実に読む
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_env_path, override=True)

from freee_expense.client import FreeeClient, ExpenseLine, ExpenseApplication

# 画像から読み取った利用履歴（チャージ +10,000 は除外）
ENTRIES = [
    # (月, 日, 乗車駅, 降車駅, 金額)
    (4,  3,  "逗子葉山",   "京急横浜",   347),
    (4,  3,  "相鉄横浜",   "星川",       188),
    (4,  3,  "日ノ出町",   "逗子葉山",   347),
    (4,  8,  "逗子葉山",   "京急横浜",   347),
    (4,  8,  "相鉄横浜",   "星川",       188),
    (4,  8,  "星川",       "相鉄横浜",   188),
    (4,  8,  "市営横浜",   "市営桜木",   210),
    (4, 10,  "逗子葉山",   "京急横浜",   347),
    (4, 10,  "相鉄横浜",   "星川",       188),
    (4, 10,  "星川",       "相鉄横浜",   188),
    (4, 10,  "京急横浜",   "逗子葉山",   347),
    (4, 11,  "京急バス",   "",           250),
    (4, 12,  "逗子葉山",   "京急弘明",   313),
    (4, 12,  "京急弘明",   "逗子葉山",   313),
    (4, 15,  "逗子葉山",   "京急横浜",   347),
    (4, 15,  "相鉄横浜",   "星川",       188),
    (4, 15,  "星川",       "相鉄横浜",   188),
    (4, 15,  "京急横浜",   "逗子葉山",   347),
    (4, 17,  "逗子葉山",   "京急横浜",   347),
    (4, 17,  "相鉄横浜",   "星川",       188),
    (4, 17,  "天王町",     "相鉄横浜",   157),
    (4, 17,  "京急横浜",   "逗子葉山",   347),
    (4, 20,  "荻窪",       "地下鉄大手町", 408),
    (4, 20,  "東京",       "逗子",       1034),
    (4, 21,  "逗子",       "馬喰町",     1034),
    (4, 21,  "馬喰横山",   "都市ヶ谷",   220),
    (4, 21,  "都市ヶ谷",   "馬喰横山",   220),
    (4, 22,  "馬喰町",     "逗子",       1034),
    (4, 24,  "逗子葉山",   "京急横浜",   347),
    (4, 24,  "相鉄横浜",   "星川",       188),
    (4, 24,  "星川",       "相鉄横浜",   188),
    (4, 24,  "横浜",       "横浜",       160),
    (4, 24,  "市営横浜",   "市営関内",   210),
    (4, 24,  "市営関内",   "市営上大岡", 242),
    (4, 24,  "京急上大",   "逗子葉山",   313),
    (4, 28,  "逗子",       "恵比寿",     1034),
    (4, 28,  "恵比寿",     "逗子",       1034),
]

YEAR = 2026
TITLE = "経費精算申請1/3"
DESCRIPTION = "打ち合わせ"
ACCOUNT_NAME = "交通費（電車在来線・バス）"


def main():
    import requests as _req
    _tok = os.getenv("FREEE_ACCESS_TOKEN", "")
    print(f"[debug] token prefix : {_tok[:20] if _tok else '(empty)'}")
    _r = _req.get("https://api.freee.co.jp/api/1/users/me",
                  headers={"Authorization": f"Bearer {_tok}"}, timeout=10)
    print(f"[debug] /users/me     : HTTP {_r.status_code}")
    _r2 = _req.get("https://api.freee.co.jp/api/1/companies",
                   headers={"Authorization": f"Bearer {_tok}"}, timeout=10)
    print(f"[debug] /companies    : HTTP {_r2.status_code}")
    if _r2.status_code == 200:
        for c in _r2.json().get("companies", []):
            print(f"[debug]   company: {c['display_name']} id={c['id']} role={c.get('role')}")

    # account_items を直接テスト
    _r3 = _req.get("https://api.freee.co.jp/api/1/account_items",
                   params={"company_id": 845775},
                   headers={"Authorization": f"Bearer {_tok}"}, timeout=10)
    print(f"[debug] /account_items: HTTP {_r3.status_code}")
    print(f"[debug] response body : {_r3.text[:400]}")

    client = FreeeClient()
    print(f"[debug] client token : {client._access_token[:20] if client._access_token else '(empty)'}")

    # 勘定科目を検索（部分一致）
    all_items = client.get_account_items()
    account_item = None
    for item in all_items:
        if "交通費" in item["name"] or "旅費交通費" in item["name"]:
            account_item = item
            print(f"勘定科目: {item['name']} (ID={item['id']})")
            break

    if account_item is None:
        print(f"エラー: 勘定科目「{ACCOUNT_NAME}」が見つかりません。")
        print("利用可能な勘定科目:")
        for item in all_items:
            print(f"  {item['name']}")
        sys.exit(1)

    account_item_id = account_item["id"]

    # 明細を組み立て
    lines = []
    total = 0
    for month, day, from_st, to_st, amount in ENTRIES:
        expense_date = date(YEAR, month, day)
        if to_st:
            desc = f"{DESCRIPTION}（{from_st} → {to_st}）"
        else:
            desc = f"{DESCRIPTION}（{from_st}）"

        lines.append(ExpenseLine(
            amount=amount,
            description=desc,
            expense_date=expense_date,
            account_item_id=account_item_id,
        ))
        total += amount
        print(f"  {expense_date}  {desc}  ¥{amount:,}")

    print(f"\n合計: {len(lines)} 件 / ¥{total:,}")
    print("\nfreee に申請を作成中...")

    application = ExpenseApplication(
        title=TITLE,
        lines=lines,
        description=f"2026年4月分 Suica 交通費 {len(lines)}件 合計¥{total:,}",
    )
    result = client.create_expense_application(application)
    print(f"\n完了！申請ID: {result['id']}")


if __name__ == "__main__":
    main()
