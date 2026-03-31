"""
Stationwork (JR 東日本) 領収書ダウンローダー

https://www.stationwork.jp にログインし、
指定月の利用明細 PDF をダウンロードする。

環境変数:
  STATIONWORK_EMAIL    : Stationwork ログイン ID（メールアドレス）
  STATIONWORK_PASSWORD : Stationwork パスワード
"""
from __future__ import annotations

import os
import time

from dotenv import load_dotenv

from .base import BaseReceiptDownloader

load_dotenv()

LOGIN_URL = "https://www.stationwork.jp/login"
BILLING_URL = "https://www.stationwork.jp/mypage/billing"


class StationworkDownloader(BaseReceiptDownloader):
    service_name = "Stationwork"

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        download_dir: str = "downloads",
        headless: bool = True,
    ):
        super().__init__(download_dir=download_dir, headless=headless)
        self.email = email or os.getenv("STATIONWORK_EMAIL", "")
        self.password = password or os.getenv("STATIONWORK_PASSWORD", "")

        if not self.email or not self.password:
            raise ValueError(
                "STATIONWORK_EMAIL と STATIONWORK_PASSWORD を .env に設定してください。"
            )

    def _login(self):
        page = self.page
        page.goto(LOGIN_URL, wait_until="networkidle")

        # ログインフォーム入力
        page.fill('input[type="email"], input[name*="email"], input[name*="login_id"]', self.email)
        page.fill('input[type="password"]', self.password)
        page.click('button[type="submit"], input[type="submit"]')
        page.wait_for_load_state("networkidle")

        if "login" in page.url.lower():
            raise RuntimeError("Stationwork へのログインに失敗しました。認証情報を確認してください。")

        print(f"  [{self.service_name}] ログイン成功")

    def _download(self, year: int, month: int) -> list[str]:
        self._login()

        page = self.page
        downloaded: list[str] = []

        # 利用明細ページへ
        page.goto(BILLING_URL, wait_until="networkidle")
        time.sleep(2)

        # 年月を選択（ページの UI に応じて調整）
        try:
            # 年月セレクター or ページネーション
            target_text = f"{year}年{month}月"
            month_links = page.query_selector_all(f'a:has-text("{target_text}"), td:has-text("{target_text}")')
            if month_links:
                month_links[0].click()
                page.wait_for_load_state("networkidle")
                time.sleep(1)
        except Exception:
            pass

        # 「領収書」「明細」「PDF」リンクを探す
        selectors = [
            'a:has-text("領収書")',
            'a:has-text("請求書")',
            'a:has-text("明細")',
            'a[href*="receipt"]',
            'a[href*="invoice"]',
            'a[href$=".pdf"]',
            'button:has-text("ダウンロード")',
        ]

        for selector in selectors:
            links = page.query_selector_all(selector)
            if links:
                for i, link in enumerate(links):
                    try:
                        with page.expect_download(timeout=30000) as dl_info:
                            link.click()
                        download = dl_info.value
                        filename = f"stationwork_{year}{month:02d}_{i+1:02d}.pdf"
                        save_path = os.path.join(self.download_dir, filename)
                        download.save_as(save_path)
                        downloaded.append(save_path)
                        print(f"  保存: {filename}")
                    except Exception:
                        # ダウンロードが始まらない場合は現在のページを PDF 保存
                        try:
                            link.click()
                            page.wait_for_load_state("networkidle")
                            filename = f"stationwork_{year}{month:02d}_{i+1:02d}.pdf"
                            path = self._save_pdf_from_page(filename)
                            downloaded.append(path)
                            print(f"  保存 (PDF印刷): {filename}")
                            page.go_back(wait_until="networkidle")
                        except Exception as e2:
                            print(f"  [警告] {e2}")
                break

        if not downloaded:
            # フォールバック: 明細ページ全体を PDF 化
            print(f"  ダウンロードリンクが見つからないため、明細ページを PDF 保存します。")
            filename = f"stationwork_{year}{month:02d}_billing.pdf"
            path = self._save_pdf_from_page(filename)
            downloaded.append(path)
            print(f"  保存: {filename}")

        return downloaded
