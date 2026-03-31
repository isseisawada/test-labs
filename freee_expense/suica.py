"""
モバイル Suica 利用履歴 CSV → freee 交通費登録

モバイル Suica アプリ:
  「利用履歴」→「CSVダウンロード」で取得できる CSV を読み込む。

CSV フォーマット（モバイル Suica 標準）:
  年月日, 種別, 出場（降車）, 入場（乗車）, 残高, 入金, 利用額

交通費として扱う種別: 電車, バス
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date
from typing import TextIO

# 交通費として処理する種別キーワード
TRANSIT_KINDS = {"電車", "バス", "バス等", "新幹線"}

# freee の勘定科目名（旅費交通費）
ACCOUNT_ITEM_NAME = "旅費交通費"


@dataclass
class SuicaEntry:
    """Suica 1件分の乗車記録"""
    expense_date: date
    kind: str          # 種別（電車、バス など）
    departure: str     # 乗車駅
    arrival: str       # 降車駅
    amount: int        # 利用額（円）

    @property
    def description(self) -> str:
        if self.departure and self.arrival:
            return f"{self.departure} → {self.arrival}"
        return self.kind

    def __str__(self) -> str:
        return f"{self.expense_date}  {self.description}  ¥{self.amount:,}"


def _parse_date(s: str) -> date:
    """
    '2024/03/15' や '2024-03-15' や '令和6年3月15日' などを date に変換する
    """
    s = s.strip()
    # YYYY/MM/DD or YYYY-MM-DD
    m = re.match(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # 元号（令和・平成・昭和）
    era_map = {"令和": 2018, "平成": 1988, "昭和": 1925}
    for era, base in era_map.items():
        m2 = re.match(rf"{era}(\d+)年(\d+)月(\d+)日", s)
        if m2:
            y = base + int(m2.group(1))
            return date(y, int(m2.group(2)), int(m2.group(3)))
    raise ValueError(f"日付のパースに失敗しました: {s!r}")


def _parse_amount(s: str) -> int:
    """' -230' や '230' や '¥230' などを整数に変換する"""
    s = re.sub(r"[¥,\s]", "", s)
    if not s or s == "-":
        return 0
    return abs(int(s))


def parse_suica_csv(source: str | TextIO, encoding: str = "cp932") -> list[SuicaEntry]:
    """
    モバイル Suica CSV を解析して乗車記録リストを返す。

    Args:
        source: CSVファイルパス (str) または file-like オブジェクト
        encoding: ファイルエンコーディング（デフォルト: Shift-JIS / cp932）

    Returns:
        SuicaEntry のリスト（交通費種別のみ）
    """
    if isinstance(source, str):
        with open(source, encoding=encoding, errors="replace") as f:
            content = f.read()
    else:
        content = source.read()

    # BOM 除去
    content = content.lstrip("\ufeff")

    entries: list[SuicaEntry] = []
    reader = csv.reader(io.StringIO(content))

    # ヘッダー行を読み飛ばす（「年月日」を含む行まで）
    headers: list[str] = []
    for row in reader:
        if any("年月日" in cell or "日付" in cell for cell in row):
            headers = [cell.strip() for cell in row]
            break

    if not headers:
        # ヘッダーが見つからなければ最初から試みる
        reader = csv.reader(io.StringIO(content))
        headers = []

    # カラムインデックスを特定
    def col(keywords: list[str]) -> int:
        for kw in keywords:
            for i, h in enumerate(headers):
                if kw in h:
                    return i
        return -1

    idx_date = col(["年月日", "日付", "date"])
    idx_kind = col(["種別", "区分", "kind"])
    idx_dep  = col(["入場", "乗車", "from", "発"])
    idx_arr  = col(["出場", "降車", "to", "着"])
    idx_amt  = col(["利用額", "金額", "amount", "利用金額"])

    for row in reader:
        if not row or not row[0].strip():
            continue
        try:
            if idx_date < 0 or idx_date >= len(row):
                continue
            kind = row[idx_kind].strip() if idx_kind >= 0 and idx_kind < len(row) else ""
            # 交通費以外はスキップ
            if kind and not any(k in kind for k in TRANSIT_KINDS):
                continue

            expense_date = _parse_date(row[idx_date])
            departure = row[idx_dep].strip() if idx_dep >= 0 and idx_dep < len(row) else ""
            arrival   = row[idx_arr].strip() if idx_arr >= 0 and idx_arr < len(row) else ""
            amount    = _parse_amount(row[idx_amt]) if idx_amt >= 0 and idx_amt < len(row) else 0

            if amount == 0:
                continue  # チャージ等はスキップ

            entries.append(SuicaEntry(
                expense_date=expense_date,
                kind=kind or "電車",
                departure=departure,
                arrival=arrival,
                amount=amount,
            ))
        except Exception:
            continue

    return entries


def suica_entries_to_expense_lines(entries: list[SuicaEntry], account_item_id: int) -> list[dict]:
    """
    SuicaEntry のリストを freee 経費申請明細フォーマットに変換する。

    account_item_id: freee の「旅費交通費」勘定科目 ID
    """
    from .client import ExpenseLine
    return [
        ExpenseLine(
            amount=e.amount,
            description=e.description,
            expense_date=e.expense_date,
            account_item_id=account_item_id,
        )
        for e in entries
    ]
