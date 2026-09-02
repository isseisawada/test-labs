"""
現金/PDF 領収書 → entries_receipts.json 抽出

使い方:
  1. inputs_2026MM/receipts/ 配下に領収書画像 (.jpg/.png/.pdf) を配置
  2. python3 extract_receipts.py --month 8
  → inputs_2026MM/entries_receipts.json が生成される

各領収書 1 枚 = 1 エントリ。Claude Vision で日付・金額・店名・用途を抽出する。
参加者（participants）は画像から分からないので空で出力される。
会議費・接待交際費の行は entries.json で participants を必ず埋めること。
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
    return f"""この画像は領収書です。以下 JSON オブジェクトだけを出力してください。

- date: YYYY-MM-DD（利用日・発行日。年が読み取れない/不自然なら {year} 年とする）
- vendor: 店名・発行元（正式名称）
- amount: 税込合計（整数、円マーク・カンマなし）
- kind: "receipt" 固定
- account: 用途から推定する勘定科目名。以下のいずれかを選ぶ:
    - "会議費"（喫茶・カフェ・コワーキング利用・少額の飲食）
    - "接待交際費"（会食・懇親会・飲み会など、合計が5,000円を超える飲食）
    - "交通費（タクシー等）"（タクシー領収書）
    - "交通費（電車在来線・バス）"（電車・バス）
    - "交通費（特急・新幹線）"（新幹線・特急券）
    - "ガソリン代"（ガソリンスタンド）
    - "駐車場代"（コインパーキング・駐車場）
    - "雑費"（サブスク・クラウド利用料・その他）
- description: 用途の短い説明。飲食なら「打ち合わせ（店名）」、タクシーなら「タクシー利用（乗車地→降車地）」、
  サブスクなら「サービス名 {year}年{month}月分利用料」のように書く
- participants: [] （画像からは分からないので必ず空配列）
- invoice_number: 適格請求書発行事業者の登録番号（T+13桁）。無ければ ""

出力形式（前後の説明・コードフェンスなし、JSON オブジェクトのみ）:
{{"date":"{year}-{month:02d}-15","vendor":"スターバックス","amount":540,"kind":"receipt","account":"会議費","description":"打ち合わせ（スターバックス）","participants":[],"invoice_number":""}}
"""


def encode(path: str) -> dict:
    ext = os.path.splitext(path)[1].lower()
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    if ext == ".pdf":
        return {"type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "webp": "image/webp"}.get(ext.lstrip("."), "image/jpeg")
    return {"type": "image",
            "source": {"type": "base64", "media_type": mime, "data": b64}}


def list_files(input_dir: str) -> list[str]:
    exts = ["jpg", "jpeg", "png", "pdf", "webp"]
    files: list[str] = []
    for e in exts:
        files += glob.glob(os.path.join(input_dir, f"*.{e}"))
        files += glob.glob(os.path.join(input_dir, f"*.{e.upper()}"))
    return sorted(set(files))


def extract_one(client: anthropic.Anthropic, path: str, prompt: str) -> dict | None:
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": [encode(path), {"type": "text", "text": prompt}]}],
        )
        text = resp.content[0].text.strip()
        start = text.find("{")
        end   = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        print(f"  !! 失敗: {e}")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", type=int, required=True, help="対象月（例: 8）")
    ap.add_argument("--year", type=int, default=YEAR)
    args = ap.parse_args()

    input_dir = os.path.join(HERE, f"inputs_{args.year}{args.month:02d}", "receipts")
    output    = os.path.join(HERE, f"inputs_{args.year}{args.month:02d}", "entries_receipts.json")

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("エラー: ANTHROPIC_API_KEY が .env にありません。")
        sys.exit(1)
    if not os.path.isdir(input_dir):
        print(f"{input_dir} を作成し、領収書を配置してください。")
        sys.exit(1)

    files = list_files(input_dir)
    if not files:
        print(f"{input_dir} に画像/PDF がありません。")
        sys.exit(1)

    prompt = build_prompt(args.year, args.month)
    client = anthropic.Anthropic()
    entries = []
    for p in files:
        print(f"[{os.path.basename(p)}]")
        info = extract_one(client, p, prompt)
        if not info:
            continue
        info.setdefault("participants", [])
        info["receipt_path"] = os.path.relpath(p, HERE)
        entries.append(info)
        print(f"  → {info.get('date')}  {info.get('vendor')}  ¥{info.get('amount')}  [{info.get('account')}]")

    with open(output, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"\n保存: {output}  ({len(entries)} 件)")
    print(f"→ 次: python3 merge_entries.py --month {args.month}")


if __name__ == "__main__":
    main()
