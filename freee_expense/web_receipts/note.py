"""
note 領収書ダウンローダー

https://note.com にログインし、
指定月のサブスクリプション（note pro など）の領収書 PDF をダウンロードする。

環境変数:
  NOTE_EMAIL    : note ログイン用メールアドレス
  NOTE_PASSWORD : note パスワード
"""
from __future__ import annotations

import os
import time

from dotenv import load_dotenv

from .base import BaseReceiptDownloader

load_dotenv()

LOGIN_URL = "https://note.com/login"
BILLING_URL = "https://note.com/settings/billing"
RECEIPTS_URL = "https://note.com/settings/receipts"


class NoteDownloader(BaseReceiptDownloader):
    service_name = "note"

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        download_dir: str = "downloads",
        headless: bool = True,
    ):
        super().__init__(download_dir=download_dir, headless=headless)
        self.email = email or os.getenv("NOTE_EMAIL", "")
        self.password = password or os.getenv("NOTE_PASSWORD", "")

        if not self.email or not self.password:
            raise ValueError(
                "NOTE_EMAIL と NOTE_PASSWORD を .env に設定してください。"
            )

    def _login(self):
        page = self.page
        page.goto(LOGIN_URL, wait_until="networkidle")
        time.sleep(1)

        # メールアドレスとパスワードを入力
        page.fill('input[name="login_id"], input[type="email"], input[placeholder*="メール"]', self.email)
        page.fill('input[type="password"]', self.password)
        page.click('button[type="submit"], button:has-text("ログイン")')
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # ログイン確認
        if "login" in page.url.lower() or "signin" in page.url.lower():
            raise RuntimeError("note へのログインに失敗しました。認証情報を確認してください。")

        print(f"  [{self.service_name}] ログイン成功")

    def _download(self, year: int, month: int) -> list[str]:
        self._login()

        page = self.page
        downloaded: list[str] = []

        # 領収書ページへ（/settings/receipts が存在すればそちら優先）
        for url in [RECEIPTS_URL, BILLING_URL]:
            page.goto(url, wait_until="networkidle")
            time.sleep(2)

            # 対象月の行を探す
            target_ym = f"{year}年{month}月"
            target_ym_alt = f"{year}/{month:02d}"

            # 領収書ダウンロードボタン/リンクを探す
            selectors = [
                f'tr:has-text("{target_ym}") a',
                f'tr:has-text("{target_ym_alt}") a',
                'a:has-text("領収書")',
                'a[href*="receipt"]',
                'button:has-text("領収書をダウンロード")',
                'a:has-text("請求書")',
            ]

            found = False
            for selector in selectors:
                links = page.query_selector_all(selector)
                if links:
                    for i, link in enumerate(links):
                        try:
                            with page.expect_download(timeout=30000) as dl_info:
                                link.click()
                            download = dl_info.value
                            filename = f"note_{year}{month:02d}_{i+1:02d}.pdf"
                            save_path = os.path.join(self.download_dir, filename)
                            download.save_as(save_path)
                            downloaded.append(save_path)
                            print(f"  保存: {filename}")
                            found = True
                        except Exception:
                            # ダウンロード不可なら PDF 印刷
                            try:
                                link.click()
                                page.wait_for_load_state("networkidle")
                                time.sleep(1)
                                filename = f"note_{year}{month:02d}_{i+1:02d}.pdf"
                                path = self._save_pdf_from_page(filename)
                                downloaded.append(path)
                                print(f"  保存 (PDF印刷): {filename}")
                                page.go_back(wait_until="networkidle")
                                found = True
                            except Exception as e2:
                                print(f"  [警告] {e2}")
                    break

            if found:
                break

        if not downloaded:
            # フォールバック: 請求ページを PDF 化
            print(f"  領収書リンクが見つからないため、請求ページを PDF 保存します。")
            filename = f"note_{year}{month:02d}_billing.pdf"
            path = self._save_pdf_from_page(filename)
            downloaded.append(path)
            print(f"  保存: {filename}")

        return downloaded
