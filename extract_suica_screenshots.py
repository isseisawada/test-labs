"""
Suica 利用履歴のスクリーンショット / PDF → entries_suica.json 抽出

使い方:
  1. inputs_2026MM/suica/ 配下にスクリーンショット (.png/.jpg) or PDF を配置
  2. python3 extract_suica_screenshots.py --month 8
  → inputs_2026MM/entries_suica.json が生成される

Claude Vision で駅名・日付・金額を抽出する。
チャージ（+10000 など）は除外し、乗車データのみを取得する。
"""
from __future__ import annotations

import argparse
import base64
import glob
import json
import os
import sys

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

import anthropic

HERE  = os.path.dirname(os.path.abspath(__file__))
MODEL = "claude-opus-4-7"
YEAR  = 2026


def build_prompt(year: int, month: int) -> str:
    return f"""この画像はモバイル Suica の利用履歴です。以下の JSON 配列だけを出力してください。

- 各行は 1 件の乗車データを表します
- 「入」「出」列がある場合は「入」＝乗車駅、「出」＝降車駅
- 「バス等」「バス」などバス利用の場合は「to」を空文字にする
- チャージ・入金（例: +10,000 や「カード」種別）は絶対に含めない
- 金額は絶対値の整数（マイナス記号や円マーク、カンマは除去）
- 日付は YYYY-MM-DD 形式。月日のみ表示されている場合は {year}年{month}月として補完
- {year}年{month}月 以外の行（前月分など）が混ざっていても、日付はそのまま正しく書き出す
- 駅名は表示通りに書き出す（京急横浜／相鉄横浜／市営桜木 なども原文のまま）

出力形式（前後の説明・コードフェンスなし、JSON 配列のみ）:
[
  {{"date": "{year}-{month:02d}-01", "kind": "suica", "from": "逗子", "to": "横浜", "amount": 347}},
  ...
]
"""


def encode_file(path: str) -> dict:
    """画像 or PDF を Claude API 用の content ブロックに変換"""
    ext = os.path.splitext(path)[1].lower()
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    if ext == ".pdf":
        return {"type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "webp": "image/webp", "gif": "image/gif"}.get(ext.lstrip("."), "image/png")
    return {"type": "image",
            "source": {"type": "base64", "media_type": mime, "data": b64}}


def list_files(input_dir: str) -> list[str]:
    exts = ["png", "jpg", "jpeg", "pdf", "webp"]
    files: list[str] = []
    for e in exts:
        files += glob.glob(os.path.join(input_dir, f"*.{e}"))
        files += glob.glob(os.path.join(input_dir, f"*.{e.upper()}"))
    return sorted(set(files))


def extract(files: list[str], prompt: str) -> list[dict]:
    client = anthropic.Anthropic()
    content: list[dict] = [encode_file(p) for p in files]
    content.append({"type": "text", "text": prompt})

    print(f"Vision 実行中 ({len(files)} ファイル)...")
    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        messages=[{"role": "user", "content": content}],
    )
    text = resp.content[0].text.strip()
    start = text.find("[")
    end   = text.rfind("]") + 1
    if start < 0 or end <= 0:
        print("!! JSON 配列が見つかりません")
        print(text)
        sys.exit(1)
    return json.loads(text[start:end])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", type=int, required=True, help="対象月（例: 8）")
    ap.add_argument("--year", type=int, default=YEAR)
    args = ap.parse_args()

    input_dir = os.path.join(HERE, f"inputs_{args.year}{args.month:02d}", "suica")
    output    = os.path.join(HERE, f"inputs_{args.year}{args.month:02d}", "entries_suica.json")

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("エラー: ANTHROPIC_API_KEY が .env に設定されていません。")
        sys.exit(1)
    if not os.path.isdir(input_dir):
        print(f"エラー: {input_dir} がありません。")
        print(f"  mkdir -p {input_dir}  してスクリーンショット/PDF を配置してください")
        sys.exit(1)

    files = list_files(input_dir)
    if not files:
        print(f"エラー: {input_dir} に画像/PDF がありません。")
        sys.exit(1)

    print(f"入力: {len(files)} ファイル")
    for f in files:
        print(f"  - {os.path.basename(f)}")

    entries = extract(files, build_prompt(args.year, args.month))

    # 対象月以外の行を警告（削除はしない。entries.json で判断）
    prefix = f"{args.year}-{args.month:02d}-"
    outside = [e for e in entries if not str(e.get("date", "")).startswith(prefix)]

    total = sum(int(e["amount"]) for e in entries)
    print(f"\n抽出結果: {len(entries)} 件 / ¥{total:,}")
    for e in entries:
        route = f"{e['from']} → {e['to']}" if e.get("to") else e["from"]
        mark = "  ⚠対象月外" if not str(e.get("date", "")).startswith(prefix) else ""
        print(f"  {e['date']}  {route}  ¥{int(e['amount']):,}{mark}")
    if outside:
        print(f"\n⚠ 対象月（{args.year}/{args.month}）以外の行が {len(outside)} 件あります。不要なら entries_suica.json から削除してください。")

    with open(output, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"\n保存: {output}")
    print(f"→ 次: python3 extract_receipts.py --month {args.month}")


if __name__ == "__main__":
    main()
