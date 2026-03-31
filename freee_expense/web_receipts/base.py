"""
Web 領収書ダウンローダー 基底クラス

各サービスのダウンローダーはこのクラスを継承する。
Playwright を使いブラウザを自動操作する。
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

DEFAULT_DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")


class BaseReceiptDownloader(ABC):
    """Web サービスから領収書をダウンロードする基底クラス"""

    service_name: str = "Unknown"

    def __init__(self, download_dir: str = DEFAULT_DOWNLOAD_DIR, headless: bool = True):
        self.download_dir = download_dir
        self.headless = headless
        Path(download_dir).mkdir(parents=True, exist_ok=True)
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def __enter__(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        self._context = self._browser.new_context(
            accept_downloads=True,
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
        )
        self._page = self._context.new_page()
        return self

    def __exit__(self, *_):
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("__enter__ を呼び出してください")
        return self._page

    def download(
        self,
        year: int | None = None,
        month: int | None = None,
    ) -> list[str]:
        """
        領収書をダウンロードしてファイルパスのリストを返す。

        Args:
            year: 対象年（省略時は当年）
            month: 対象月（省略時は当月）

        Returns:
            ダウンロードした PDF / 画像のパスリスト
        """
        today = date.today()
        year = year or today.year
        month = month or today.month
        print(f"[{self.service_name}] {year}/{month:02d} の領収書を取得中...")
        return self._download(year, month)

    @abstractmethod
    def _download(self, year: int, month: int) -> list[str]:
        """サービス固有のダウンロード処理"""

    def _save_pdf_from_page(self, filename: str) -> str:
        """現在のページを PDF として保存する"""
        path = os.path.join(self.download_dir, filename)
        self.page.pdf(path=path, format="A4")
        return path
