"""
領収書 OCR モジュール

Claude Vision API を使って領収書画像から以下を抽出する:
  - 金額
  - 日付
  - 店舗名 / 発行元
  - 勘定科目の候補
  - 目的（用途）
"""
from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

# 勘定科目の推定ルール（キーワード → 科目名）
ACCOUNT_ITEM_HINTS: dict[str, list[str]] = {
    "旅費交通費": ["タクシー", "電車", "バス", "飛行機", "新幹線", "Suica", "PASMO", "交通", "駐車", "高速"],
    "接待交際費": ["レストラン", "居酒屋", "カフェ", "喫茶", "ホテル", "宴会", "会食", "飲食"],
    "会議費": ["コーヒー", "会議", "ミーティング", "打ち合わせ", "スターバックス", "ドトール"],
    "消耗品費": ["文具", "コンビニ", "ホームセンター", "100円", "ダイソー", "紙", "ペン", "文房具"],
    "通信費": ["ソフトバンク", "ドコモ", "au", "楽天モバイル", "インターネット", "電話"],
    "新聞図書費": ["書籍", "本", "雑誌", "Amazon", "楽天ブックス", "書店", "ebook"],
    "水道光熱費": ["電気", "ガス", "水道", "東京電力", "東京ガス"],
    "地代家賃": ["家賃", "賃料", "レンタル"],
    "外注費": ["AWS", "Google", "Azure", "GitHub", "Slack", "Notion", "Figma", "Adobe"],
    "広告宣伝費": ["広告", "Google Ads", "Facebook", "Twitter", "Instagram"],
}


@dataclass
class ReceiptInfo:
    """OCR で抽出した領収書情報"""
    amount: int                        # 金額（税込み、円）
    expense_date: date                 # 日付
    vendor: str                        # 店舗名 / 発行元
    description: str                   # 内容・目的
    account_item_name: str             # 推奨勘定科目名
    raw_text: str = ""                 # OCR で得られた生テキスト

    def __str__(self) -> str:
        return (
            f"  店舗     : {self.vendor}\n"
            f"  日付     : {self.expense_date}\n"
            f"  金額     : ¥{self.amount:,}\n"
            f"  勘定科目 : {self.account_item_name}\n"
            f"  目的     : {self.description}"
        )


def _encode_image(file_path: str) -> tuple[str, str]:
    """画像を base64 エンコードして (base64_data, media_type) を返す"""
    ext = Path(file_path).suffix.lower()
    if ext in (".jpg", ".jpeg"):
        media_type = "image/jpeg"
    elif ext == ".png":
        media_type = "image/png"
    elif ext == ".gif":
        media_type = "image/gif"
    elif ext == ".webp":
        media_type = "image/webp"
    else:
        raise ValueError(f"サポートされていない画像形式: {ext}")

    with open(file_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8"), media_type


def _guess_account_item(vendor: str, description: str) -> str:
    """店舗名と説明から勘定科目を推定する"""
    text = vendor + " " + description
    for account_name, keywords in ACCOUNT_ITEM_HINTS.items():
        if any(kw in text for kw in keywords):
            return account_name
    return "消耗品費"  # デフォルト


PROMPT = """
この領収書画像から以下の情報を JSON で抽出してください。
必ず JSON のみを返し、余分な説明は不要です。

{
  "amount": <税込み合計金額（整数、円）>,
  "date": "<日付 YYYY-MM-DD 形式>",
  "vendor": "<店舗名または発行元>",
  "description": "<購入内容・用途の簡潔な説明>",
  "account_item": "<最も適切な勘定科目（旅費交通費/接待交際費/会議費/消耗品費/通信費/新聞図書費/外注費/広告宣伝費/その他）>"
}

金額は税込みの合計金額を整数で。
日付が読めない場合は今日の日付を入れてください。
勘定科目が不明な場合は「消耗品費」にしてください。
"""


def extract_receipt_info(file_path: str, api_key: str | None = None) -> ReceiptInfo:
    """
    領収書画像から情報を抽出する。

    Args:
        file_path: 領収書画像のパス（JPEG / PNG / GIF / WebP）
        api_key: Anthropic API キー（省略時は環境変数 ANTHROPIC_API_KEY を使用）

    Returns:
        ReceiptInfo
    """
    client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
    image_data, media_type = _encode_image(file_path)

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    )

    raw = message.content[0].text.strip()

    # ```json ... ``` ブロックがあれば取り除く
    raw_clean = re.sub(r"^```[a-z]*\n?", "", raw)
    raw_clean = re.sub(r"\n?```$", "", raw_clean).strip()

    data = json.loads(raw_clean)

    expense_date = date.fromisoformat(data["date"])
    account_item = data.get("account_item") or _guess_account_item(
        data.get("vendor", ""), data.get("description", "")
    )

    return ReceiptInfo(
        amount=int(data["amount"]),
        expense_date=expense_date,
        vendor=data.get("vendor", ""),
        description=data.get("description", ""),
        account_item_name=account_item,
        raw_text=raw,
    )


def extract_receipts_batch(file_paths: list[str], api_key: str | None = None) -> list[ReceiptInfo]:
    """複数の領収書を一括 OCR する"""
    results = []
    for path in file_paths:
        print(f"OCR 処理中: {os.path.basename(path)}")
        try:
            info = extract_receipt_info(path, api_key)
            print(f"  -> ¥{info.amount:,} / {info.vendor} / {info.account_item_name}")
            results.append(info)
        except Exception as e:
            print(f"  [エラー] {e}")
    return results
