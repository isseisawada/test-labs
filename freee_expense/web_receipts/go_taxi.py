"""
GO タクシーアプリ 領収書ダウンローダー

GO ビジネスアカウント (business.goinc.jp) にログインし、
指定月の乗車履歴 PDF を一括ダウンロードする。

環境変数:
  GO_EMAIL    : GO アカウントのメールアドレス
  GO_PASSWORD : GO アカウントのパスワード
"""
from __future__ import annotations

import os
import time

from dotenv import load_dotenv

from .base import BaseReceiptDownloader

load_dotenv()

GO_LOGIN_URL = "https://business.goinc.jp/login"
GO_HISTORY_URL = "https://business.goinc.jp/rides"


class GoTaxiDownloader(BaseReceiptDownloader):
    service_name = "GO タクシー"

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        download_dir: str = BaseReceiptDownloader.__dict__["__init__"].__defaults__[0]
        if "__init__" in BaseReceiptDownloader.__dict__ else "downloads",
        headless: bool = True,
    ):
        super().__init__(download_dir=download_dir, headless=headless)
        self.email = email or os.getenv("GO_EMAIL", "")
        self.password = password or os.getenv("GO_PASSWORD", "")

        if not self.email or not self.password:
            raise ValueError(
                "GO_EMAIL と GO_PASSWORD を .env に設定してください。"
            )

    def _login(self):
        page = self.page
        page.goto(GO_LOGIN_URL, wait_until="networkidle")

        # メールアドレスとパスワードを入力
        page.fill('input[type="email"], input[name="email"]', self.email)
        page.fill('input[type="password"], input[name="password"]', self.password)
        page.click('button[type="submit"], input[type="submit"]')
        page.wait_for_load_state("networkidle")

        # ログイン失敗チェック
        if "login" in page.url.lower() or "signin" in page.url.lower():
            raise RuntimeError("GO タクシーへのログインに失敗しました。認証情報を確認してください。")

        print(f"  [{self.service_name}] ログイン成功")

    def _download(self, year: int, month: int) -> list[str]:
        self._login()

        page = self.page
        downloaded: list[str] = []

        # 乗車履歴ページへ移動
        page.goto(GO_HISTORY_URL, wait_until="networkidle")
        time.sleep(2)

        # 年月フィルター（UI の構造によって調整が必要な場合あり）
        try:
            # 月フィルターセレクトボックス
            page.select_option('select[name="month"], select[id*="month"]', f"{year}-{month:02d}")
            page.wait_for_load_state("networkidle")
        except Exception:
            # フィルターが見つからない場合はスキップ
            pass

        # 領収書ダウンロードリンクを全て取得
        receipt_links = page.query_selector_all(
            'a[href*="receipt"], a[href*="invoice"], button:has-text("領収書")'
        )

        if not receipt_links:
            print(f"  [{self.service_name}] {year}/{month:02d} に領収書が見つかりませんでした。")
            return []

        for i, link in enumerate(receipt_links):
            try:
                with page.expect_download(timeout=30000) as dl_info:
                    link.click()
                download = dl_info.value
                filename = f"go_taxi_{year}{month:02d}_{i+1:02d}.pdf"
                save_path = os.path.join(self.download_dir, filename)
                download.save_as(save_path)
                downloaded.append(save_path)
                print(f"  保存: {filename}")
            except Exception as e:
                # PDF が直接表示される場合はページ保存にフォールバック
                try:
                    filename = f"go_taxi_{year}{month:02d}_{i+1:02d}.pdf"
                    path = self._save_pdf_from_page(filename)
                    downloaded.append(path)
                    print(f"  保存 (PDF印刷): {filename}")
                except Exception as e2:
                    print(f"  [警告] 領収書 {i+1} の取得に失敗: {e2}")

        return downloaded
