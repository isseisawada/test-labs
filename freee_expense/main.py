"""
freee 経費精算 CLI

使い方:
  # 初回認証
  python -m freee_expense setup

  # 領収書画像を OCR して経費申請
  python -m freee_expense receipt photo1.jpg photo2.png

  # Suica CSV を読み込んで交通費申請
  python -m freee_expense suica suica_history.csv

  # ドライラン（freee には送信せず内容確認のみ）
  python -m freee_expense receipt --dry-run photo1.jpg
  python -m freee_expense suica --dry-run suica_history.csv
"""
from __future__ import annotations

import argparse
import sys
from datetime import date

from dotenv import load_dotenv

load_dotenv()


# --------------------------------------------------------------------------- #
# 領収書フロー
# --------------------------------------------------------------------------- #

def cmd_receipt(args: argparse.Namespace):
    from .ocr import extract_receipt_info
    from .client import FreeeClient, ExpenseLine, ExpenseApplication

    files: list[str] = args.files
    dry_run: bool = args.dry_run
    title: str = args.title or f"経費申請 {date.today()}"

    print(f"=== 領収書 OCR ({len(files)} 件) ===")
    infos = []
    for f in files:
        print(f"\n[{f}]")
        try:
            info = extract_receipt_info(f)
            print(info)
            infos.append((f, info))
        except Exception as e:
            print(f"  [スキップ] OCR エラー: {e}")

    if not infos:
        print("処理できる領収書がありませんでした。")
        sys.exit(1)

    if dry_run:
        print("\n[ドライラン] freee への送信はスキップします。")
        return

    # freee に登録
    client = FreeeClient()
    account_items = {a["name"]: a["id"] for a in client.get_expense_account_items()}

    lines = []
    receipt_ids = []
    for file_path, info in infos:
        # 領収書をアップロード
        try:
            rid = client.upload_receipt(file_path)
            receipt_ids.append(rid)
        except Exception as e:
            print(f"  [警告] 領収書アップロード失敗: {e}")
            rid = None

        # 勘定科目 ID を解決
        account_item_id = account_items.get(info.account_item_name)
        if account_item_id is None:
            # 部分一致フォールバック
            for name, aid in account_items.items():
                if info.account_item_name in name or name in info.account_item_name:
                    account_item_id = aid
                    break
        if account_item_id is None:
            # 消耗品費をデフォルトに
            account_item_id = account_items.get("消耗品費", next(iter(account_items.values())))

        lines.append(ExpenseLine(
            amount=info.amount,
            description=f"{info.vendor} {info.description}".strip(),
            expense_date=info.expense_date,
            account_item_id=account_item_id,
            receipt_ids=[rid] if rid else [],
        ))

    application = ExpenseApplication(title=title, lines=lines)
    client.create_expense_application(application)


# --------------------------------------------------------------------------- #
# Suica フロー
# --------------------------------------------------------------------------- #

def cmd_suica(args: argparse.Namespace):
    from .suica import parse_suica_csv, suica_entries_to_expense_lines
    from .client import FreeeClient, ExpenseApplication

    csv_path: str = args.csv_file
    dry_run: bool = args.dry_run
    title: str = args.title or f"交通費申請 {date.today()}"

    print(f"=== Suica CSV 解析: {csv_path} ===")
    entries = parse_suica_csv(csv_path)

    if not entries:
        print("交通費の記録が見つかりませんでした。")
        sys.exit(1)

    total = sum(e.amount for e in entries)
    print(f"\n{len(entries)} 件の乗車記録 (合計 ¥{total:,})")
    for e in entries:
        print(f"  {e}")

    if dry_run:
        print("\n[ドライラン] freee への送信はスキップします。")
        return

    client = FreeeClient()

    # 旅費交通費の勘定科目 ID を取得
    transit_item = client.find_account_item("旅費交通費")
    if not transit_item:
        print("エラー: 勘定科目「旅費交通費」が見つかりません。freee の設定を確認してください。")
        sys.exit(1)
    account_item_id = transit_item["id"]

    lines = suica_entries_to_expense_lines(entries, account_item_id)
    application = ExpenseApplication(title=title, lines=lines)
    client.create_expense_application(application)


# --------------------------------------------------------------------------- #
# セットアップフロー
# --------------------------------------------------------------------------- #

def cmd_setup(_args: argparse.Namespace):
    from .auth import run_auth_flow
    run_auth_flow()


# --------------------------------------------------------------------------- #
# CLI エントリポイント
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m freee_expense",
        description="freee 経費精算 自動化ツール",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # setup
    sub.add_parser("setup", help="freee OAuth2 認証セットアップ")

    # receipt
    p_receipt = sub.add_parser("receipt", help="領収書画像を OCR して経費申請")
    p_receipt.add_argument("files", nargs="+", metavar="IMAGE", help="領収書画像ファイル（JPEG/PNG）")
    p_receipt.add_argument("--title", help="申請タイトル（省略時は自動生成）")
    p_receipt.add_argument("--dry-run", action="store_true", help="freee へ送信せず内容確認のみ")

    # suica
    p_suica = sub.add_parser("suica", help="Suica CSV を読み込んで交通費申請")
    p_suica.add_argument("csv_file", metavar="CSV", help="モバイル Suica 利用履歴 CSV")
    p_suica.add_argument("--title", help="申請タイトル（省略時は自動生成）")
    p_suica.add_argument("--dry-run", action="store_true", help="freee へ送信せず内容確認のみ")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "setup":   cmd_setup,
        "receipt": cmd_receipt,
        "suica":   cmd_suica,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
