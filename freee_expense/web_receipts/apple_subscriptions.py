"""
Apple サブスクリプション領収書 ダウンローダー（IMAP メール取得）

Apple はサブスクリプション課金時に以下の件名でメールを送ってくる:
  - "Your receipt from Apple." （英語）
  - "Apple からの領収書" （日本語）
  - "NewsPicks" など商品名が含まれる

IMAP でメールボックスを検索し、指定月の Apple 領収書メールを
PDF として保存する。

対応メールサービス:
  - Gmail (imap.gmail.com)
  - iCloud / Apple Mail (imap.mail.me.com)
  - その他 IMAP 対応サービス

Gmail の場合は「アプリパスワード」を使用してください:
  https://myaccount.google.com/apppasswords

環境変数:
  APPLE_RECEIPT_IMAP_HOST     : IMAP サーバー（例: imap.gmail.com）
  APPLE_RECEIPT_IMAP_PORT     : ポート番号（デフォルト: 993）
  APPLE_RECEIPT_EMAIL         : メールアドレス
  APPLE_RECEIPT_APP_PASSWORD  : アプリパスワード
"""
from __future__ import annotations

import email
import imaplib
import os
import re
import time
from datetime import date, timedelta
from email.header import decode_header
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Apple の差出人ドメイン
APPLE_SENDERS = [
    "no_reply@email.apple.com",
    "noreply@email.apple.com",
    "no-reply@apple.com",
    "receipts@apple.com",
]

# 件名キーワード
SUBJECT_KEYWORDS = [
    "receipt from Apple",
    "Apple からの領収書",
    "Apple の領収書",
    "Your receipt",
    "NewsPicks",
]


def _decode_str(s: str | bytes | None) -> str:
    """メールヘッダー文字列をデコードする"""
    if s is None:
        return ""
    if isinstance(s, bytes):
        decoded, charset = decode_header(s.decode("ascii", errors="replace"))[0]
        if isinstance(decoded, bytes):
            return decoded.decode(charset or "utf-8", errors="replace")
        return decoded
    parts = decode_header(s)
    result = ""
    for part, charset in parts:
        if isinstance(part, bytes):
            result += part.decode(charset or "utf-8", errors="replace")
        else:
            result += part
    return result


class AppleSubscriptionReceiptFetcher:
    """IMAP で Apple 領収書メールを取得し PDF として保存する"""

    service_name = "Apple サブスクリプション (Newspicks)"

    def __init__(
        self,
        imap_host: str | None = None,
        imap_port: int | None = None,
        email_address: str | None = None,
        app_password: str | None = None,
        download_dir: str = "downloads",
        target_apps: list[str] | None = None,
    ):
        self.imap_host = imap_host or os.getenv("APPLE_RECEIPT_IMAP_HOST", "imap.gmail.com")
        self.imap_port = imap_port or int(os.getenv("APPLE_RECEIPT_IMAP_PORT", "993"))
        self.email_address = email_address or os.getenv("APPLE_RECEIPT_EMAIL", "")
        self.app_password = app_password or os.getenv("APPLE_RECEIPT_APP_PASSWORD", "")
        self.download_dir = download_dir
        # アプリ名フィルター（指定しない場合は全 Apple 領収書）
        self.target_apps = target_apps or ["NewsPicks", "ニューズピックス"]

        Path(download_dir).mkdir(parents=True, exist_ok=True)

        if not self.email_address or not self.app_password:
            raise ValueError(
                "APPLE_RECEIPT_EMAIL と APPLE_RECEIPT_APP_PASSWORD を .env に設定してください。\n"
                "Gmail の場合は「アプリパスワード」を使用してください:\n"
                "  https://myaccount.google.com/apppasswords"
            )

    def download(self, year: int | None = None, month: int | None = None) -> list[str]:
        today = date.today()
        year = year or today.year
        month = month or today.month
        print(f"[{self.service_name}] {year}/{month:02d} の領収書メールを検索中...")
        return self._fetch(year, month)

    def _fetch(self, year: int, month: int) -> list[str]:
        # 検索日付範囲
        start = date(year, month, 1)
        # 翌月1日
        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)

        # IMAP 接続
        with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as imap:
            imap.login(self.email_address, self.app_password)
            imap.select("INBOX")

            # 日付範囲と差出人で検索
            # IMAP の日付フォーマット: DD-Mon-YYYY
            since_str = start.strftime("%d-%b-%Y")
            before_str = end.strftime("%d-%b-%Y")

            search_criteria = (
                f'(SINCE "{since_str}" BEFORE "{before_str}"'
                f' OR FROM "apple.com" FROM "email.apple.com")'
            )

            _, msg_nums = imap.search(None, search_criteria)
            ids = msg_nums[0].split()

            if not ids:
                print(f"  [{self.service_name}] 対象メールが見つかりませんでした。")
                return []

            print(f"  {len(ids)} 件のメールをスキャン中...")
            downloaded = []

            for num in ids:
                _, data = imap.fetch(num, "(RFC822)")
                raw = data[0][1]
                msg = email.message_from_bytes(raw)

                subject = _decode_str(msg.get("Subject", ""))
                sender = msg.get("From", "")

                # Apple からの領収書か確認
                is_apple = any(domain in sender for domain in APPLE_SENDERS)
                is_receipt = any(kw.lower() in subject.lower() for kw in SUBJECT_KEYWORDS)

                if not (is_apple or is_receipt):
                    continue

                # 対象アプリのフィルター
                if self.target_apps:
                    body = self._get_body(msg)
                    if not any(app.lower() in body.lower() or app.lower() in subject.lower()
                               for app in self.target_apps):
                        continue

                print(f"  見つかりました: {subject}")

                # 添付 PDF があれば保存
                pdf_saved = False
                for part in msg.walk():
                    if part.get_content_type() == "application/pdf":
                        filename = _decode_str(part.get_filename()) or f"apple_{year}{month:02d}.pdf"
                        filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
                        save_path = os.path.join(self.download_dir, filename)
                        with open(save_path, "wb") as f:
                            f.write(part.get_payload(decode=True))
                        downloaded.append(save_path)
                        print(f"  保存 (PDF添付): {filename}")
                        pdf_saved = True

                # PDF なければ HTML メール本文を PDF 化
                if not pdf_saved:
                    filename = f"apple_newspicks_{year}{month:02d}.pdf"
                    save_path = self._save_html_as_pdf(msg, filename)
                    if save_path:
                        downloaded.append(save_path)
                        print(f"  保存 (HTML→PDF): {filename}")

        return downloaded

    def _get_body(self, msg: email.message.Message) -> str:
        """メール本文テキストを取得する"""
        body = ""
        for part in msg.walk():
            ct = part.get_content_type()
            if ct in ("text/plain", "text/html"):
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body += payload.decode(charset, errors="replace")
        return body

    def _save_html_as_pdf(self, msg: email.message.Message, filename: str) -> str | None:
        """HTML メール本文を Playwright で PDF 化して保存する"""
        try:
            from playwright.sync_api import sync_playwright
            import tempfile

            html_body = ""
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        html_body = payload.decode(charset, errors="replace")
                        break

            if not html_body:
                return None

            save_path = os.path.join(self.download_dir, filename)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_content(html_body, wait_until="networkidle")
                page.pdf(path=save_path, format="A4")
                browser.close()

            return save_path

        except Exception as e:
            print(f"  [警告] HTML→PDF 変換失敗: {e}")
            return None
