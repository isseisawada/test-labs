"""
現金/PDF 領収書 → entries.json 抽出

使い方:
  1. inputs_202607/receipts/ 配下に領収書画像 (.jpg/.png/.pdf) を配置
  2. python3 extract_receipts.py
  → inputs_202607/entries_receipts.json が生成される

各領収書 1 枚 = 1 エントリ。Claude Vision で日付・金額・店名・用途を抽出する。
"""
from __future__ import annotations

import base64
import glob
import json
import os
import sys

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

import anthropic

MODEL     = "claude-opus-4-7"
INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "inputs_202607", "receipts")
OUTPUT    = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "inputs_202607", "entries_receipts.json")

PROMPT = """この画像は領収書です。以下 JSON オブジェクトだけを出力してください。

- date: YYYY-MM-DD（発行日）
- vendor: 店名・発行元
- amount: 税込合計（整数、円マーク・カンマなし）
- kind: "receipt" 固定
- account: 用途から推定する勘定科目名。以下のいずれかから最も近いものを選ぶ:
    - "会議費"（喫茶、レストラン、会議飲食）
    - "交通費（タクシー等）"（タクシー領収書）
    - "交通費（電車在来線・バス）"（電車・バス）
    - "通信費"（携帯、インターネット）
    - "雑費"（上記以外）
- description: 「打ち合わせ（店名）」など簡潔な用途

出力形式（前後の説明・コードフェンスなし、JSON オブジェクトのみ）:
{"date":"2026-07-15","vendor":"スターバックス","amount":540,"kind":"receipt","account":"会議費","description":"打ち合わせ（スターバックス）"}
"""


def encode(path: str) -> dict:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return {"type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "webp": "image/webp"}.get(ext.lstrip("."), "image/jpeg")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return {"type": "image",
            "source": {"type": "base64", "media_type": mime, "data": b64}}


def extract_one(client: anthropic.Anthropic, path: str) -> dict | None:
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": [encode(path), {"type": "text", "text": PROMPT}]}],
        )
        text = resp.content[0].text.strip()
        start = text.find("{")
        end   = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        print(f"  !! 失敗: {e}")
        return None


def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("エラー: ANTHROPIC_API_KEY が .env にありません。")
        sys.exit(1)

    if not os.path.isdir(INPUT_DIR):
        print(f"{INPUT_DIR} を作成し、領収書を配置してください。")
        sys.exit(1)

    files = sorted(
        glob.glob(os.path.join(INPUT_DIR, "*.jpg")) +
        glob.glob(os.path.join(INPUT_DIR, "*.jpeg")) +
        glob.glob(os.path.join(INPUT_DIR, "*.png")) +
        glob.glob(os.path.join(INPUT_DIR, "*.pdf"))
    )
    if not files:
        print(f"{INPUT_DIR} に画像/PDF がありません。")
        sys.exit(1)

    client = anthropic.Anthropic()
    entries = []
    for p in files:
        print(f"[{os.path.basename(p)}]")
        info = extract_one(client, p)
        if not info:
            continue
        info["receipt_path"] = os.path.relpath(p, os.path.dirname(os.path.abspath(__file__)))
        entries.append(info)
        print(f"  → {info.get('date')}  {info.get('vendor')}  ¥{info.get('amount')}  [{info.get('account')}]")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"\n保存: {OUTPUT}")
    print(f"→ 必要に応じて手動で inputs_202607/entries.json にマージしてください。")


if __name__ == "__main__":
    main()
