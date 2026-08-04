"""
Suica 利用履歴のスクリーンショット → entries.json 抽出

使い方:
  1. inputs_202607/suica/ 配下にスクリーンショット画像 (.png/.jpg) を配置
  2. python3 extract_suica_screenshots.py
  → inputs_202607/entries_suica.json が生成される
  → その内容を手動で inputs_202607/entries.json にマージ

Claude Vision (claude-opus-4-7) で駅名・日付・金額を抽出する。
チャージ（+10000 など）は除外し、乗車データのみを取得する。
"""
from __future__ import annotations

import base64
import glob
import json
import os
import sys
from datetime import date

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

import anthropic

MODEL     = "claude-opus-4-7"
INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "inputs_202607", "suica")
OUTPUT    = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "inputs_202607", "entries_suica.json")
YEAR      = 2026
MONTH_HINT = 7  # 迷った場合の推定月

PROMPT = f"""この画像はモバイル Suica の利用履歴です。以下の JSON 配列だけを出力してください。

- 各行は 1 件の乗車データを表します
- 「入」「出」列がある場合は「入」＝乗車駅、「出」＝降車駅
- 「バス等」「バス」などバス利用の場合は「to」を空文字にする
- チャージ・入金（例: +10,000 や「カード」種別）は絶対に含めない
- 金額は絶対値の整数（マイナス記号や円マーク、カンマは除去）
- 日付は YYYY-MM-DD 形式。月日のみ表示されている場合は {YEAR}年{MONTH_HINT}月として補完
- 駅名は表示通りに書き出す（京急横浜／相鉄横浜／市営桜木 なども原文のまま）

出力形式（前後の説明・コードフェンスなし、JSON 配列のみ）:
[
  {{"date": "2026-07-01", "kind": "suica", "from": "逗子", "to": "横浜", "amount": 347}},
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


def extract(files: list[str]) -> list[dict]:
    client = anthropic.Anthropic()

    content: list[dict] = [encode_file(p) for p in files]
    content.append({"type": "text", "text": PROMPT})

    print(f"Vision 実行中 ({len(files)} 画像)...")
    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        messages=[{"role": "user", "content": content}],
    )
    text = resp.content[0].text.strip()

    # JSON 配列を抽出
    start = text.find("[")
    end   = text.rfind("]") + 1
    if start < 0 or end <= 0:
        print("!! JSON 配列が見つかりません")
        print(text)
        sys.exit(1)
    return json.loads(text[start:end])


def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("エラー: ANTHROPIC_API_KEY が .env に設定されていません。")
        sys.exit(1)

    if not os.path.isdir(INPUT_DIR):
        print(f"エラー: {INPUT_DIR} がありません。")
        print(f"  mkdir -p {INPUT_DIR}")
        print(f"  # にスクリーンショットを配置してください")
        sys.exit(1)

    files = sorted(
        glob.glob(os.path.join(INPUT_DIR, "*.png")) +
        glob.glob(os.path.join(INPUT_DIR, "*.jpg")) +
        glob.glob(os.path.join(INPUT_DIR, "*.jpeg")) +
        glob.glob(os.path.join(INPUT_DIR, "*.pdf")) +
        glob.glob(os.path.join(INPUT_DIR, "*.PNG")) +
        glob.glob(os.path.join(INPUT_DIR, "*.JPG")) +
        glob.glob(os.path.join(INPUT_DIR, "*.JPEG")) +
        glob.glob(os.path.join(INPUT_DIR, "*.PDF"))
    )
    if not files:
        print(f"エラー: {INPUT_DIR} に画像/PDF がありません。")
        sys.exit(1)

    print(f"入力画像: {len(files)} 枚")
    for f in files:
        print(f"  - {os.path.basename(f)}")

    entries = extract(files)
    total = sum(int(e["amount"]) for e in entries)
    print(f"\n抽出結果: {len(entries)} 件 / ¥{total:,}")
    for e in entries:
        route = f"{e['from']} → {e['to']}" if e.get('to') else e['from']
        print(f"  {e['date']}  {route}  ¥{int(e['amount']):,}")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"\n保存: {OUTPUT}")
    print(f"→ 内容を確認し、必要に応じて手動で inputs_202607/entries.json にマージしてください。")


if __name__ == "__main__":
    main()
