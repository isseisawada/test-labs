"""
freee Web 経費申請 自動入力スクリプト（Playwright）
2026年4月分 Suica 交通費 37件
申請タイトル: 経費精算申請1/3
"""
from __future__ import annotations

import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

FREEE_EMAIL    = os.getenv("FREEE_LOGIN_EMAIL", "")
FREEE_PASSWORD = os.getenv("FREEE_LOGIN_PASSWORD", "")
COMPANY_ID     = "845775"
TITLE          = "経費精算申請1/3"
DESCRIPTION    = "打ち合わせ"
ACCOUNT_ITEM   = "交通費（電車在来線・バス）"

SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".freee_session.json")

ENTRIES = [
    (4,  3,  "逗子葉山",   "京急横浜",     347),
    (4,  3,  "相鉄横浜",   "星川",         188),
    (4,  3,  "日ノ出町",   "逗子葉山",     347),
    (4,  8,  "逗子葉山",   "京急横浜",     347),
    (4,  8,  "相鉄横浜",   "星川",         188),
    (4,  8,  "星川",       "相鉄横浜",     188),
    (4,  8,  "市営横浜",   "市営桜木",     210),
    (4, 10,  "逗子葉山",   "京急横浜",     347),
    (4, 10,  "相鉄横浜",   "星川",         188),
    (4, 10,  "星川",       "相鉄横浜",     188),
    (4, 10,  "京急横浜",   "逗子葉山",     347),
    (4, 11,  "京急バス",   "",             250),
    (4, 12,  "逗子葉山",   "京急弘明",     313),
    (4, 12,  "京急弘明",   "逗子葉山",     313),
    (4, 15,  "逗子葉山",   "京急横浜",     347),
    (4, 15,  "相鉄横浜",   "星川",         188),
    (4, 15,  "星川",       "相鉄横浜",     188),
    (4, 15,  "京急横浜",   "逗子葉山",     347),
    (4, 17,  "逗子葉山",   "京急横浜",     347),
    (4, 17,  "相鉄横浜",   "星川",         188),
    (4, 17,  "天王町",     "相鉄横浜",     157),
    (4, 17,  "京急横浜",   "逗子葉山",     347),
    (4, 20,  "荻窪",       "地下鉄大手町", 408),
    (4, 20,  "東京",       "逗子",         1034),
    (4, 21,  "逗子",       "馬喰町",       1034),
    (4, 21,  "馬喰横山",   "都市ヶ谷",     220),
    (4, 21,  "都市ヶ谷",   "馬喰横山",     220),
    (4, 22,  "馬喰町",     "逗子",         1034),
    (4, 24,  "逗子葉山",   "京急横浜",     347),
    (4, 24,  "相鉄横浜",   "星川",         188),
    (4, 24,  "星川",       "相鉄横浜",     188),
    (4, 24,  "横浜",       "横浜",         160),
    (4, 24,  "市営横浜",   "市営関内",     210),
    (4, 24,  "市営関内",   "市営上大岡",   242),
    (4, 24,  "京急上大",   "逗子葉山",     313),
    (4, 28,  "逗子",       "恵比寿",       1034),
    (4, 28,  "恵比寿",     "逗子",         1034),
]


def wait(page: Page, ms: int = 800):
    page.wait_for_timeout(ms)


def login(page: Page):
    print("freee にログイン中...")
    page.goto("https://accounts.secure.freee.co.jp/login", wait_until="domcontentloaded")
    wait(page, 2000)

    email_sel = 'input[type="email"], input[name="email"], input[id*="email"], input[autocomplete="email"]'
    auto_ok = False
    try:
        page.wait_for_selector(email_sel, timeout=8000)
        page.fill(email_sel, FREEE_EMAIL)
        wait(page, 300)
        page.fill('input[type="password"]', FREEE_PASSWORD)
        wait(page, 300)
        page.click('button[type="submit"], input[type="submit"], button:has-text("ログイン")')
        page.wait_for_load_state("networkidle")
        wait(page, 2000)
        auto_ok = True
    except Exception:
        pass

    if not auto_ok or "login" in page.url or "accounts" in page.url:
        print("\n" + "=" * 60)
        print("【手動ログインが必要です】")
        print("開いているブラウザで freee にログインしてください。")
        print("=" * 60)
        input("\nログイン完了したら Enter を押してください... ")
        wait(page, 1000)

    if "login" in page.url or "accounts" in page.url:
        raise RuntimeError("ログインが確認できません。")
    print("  ログイン成功")


def type_station(page: Page, field_id: str, station: str):
    """駅名をオートコンプリートで入力して最初の候補を選択"""
    field = page.locator(f'#{field_id}')
    field.click(click_count=3)
    field.type(station, delay=80)
    wait(page, 1200)
    try:
        opts = page.locator('[role="option"]')
        opts.first.wait_for(timeout=4000)
        print(f"      候補: {opts.first.inner_text().strip()}")
        opts.first.click()
        wait(page, 400)
    except Exception:
        field.press("Tab")
        wait(page, 400)


def select_route(page: Page, from_st: str, to_st: str, amount: int):
    """「交通経路を選択」ダイアログで経路を検索・選択"""
    page.locator('button:has-text("交通経路を選択")').last.click()
    wait(page, 1500)

    # 出発・到着を入力
    type_station(page, "departure-station", from_st)
    type_station(page, "arrival-station",   to_st)

    # 経路検索（ボタンが有効になるまで少し待つ）
    wait(page, 500)
    search_btn = page.locator('button:has-text("経路検索")')
    try:
        search_btn.wait_for(state="enabled", timeout=3000)
    except Exception:
        pass
    search_btn.click()
    wait(page, 4000)

    # 経路結果から金額が一致するものを選ぶ、なければ最初を選択
    try:
        radios = page.locator('input[type="radio"]:not(.vb-toggleButton__input)')
        radios.first.wait_for(timeout=6000)
        count = radios.count()

        selected = False
        for i in range(count):
            # ラジオボタンの親要素のテキストで金額を確認
            try:
                parent_text = radios.nth(i).locator('xpath=ancestor::tr | xpath=ancestor::li | xpath=ancestor::div[contains(@class,"route")]').first.inner_text()
                if str(amount) in parent_text.replace(",", "").replace("￥", "").replace("¥", ""):
                    radios.nth(i).click()
                    selected = True
                    break
            except Exception:
                pass

        if not selected:
            radios.first.click()
        wait(page, 500)

        # 確定ボタン（freee のルートダイアログの閉じるボタン）
        for btn_text in ["この経路を使用", "選択して閉じる", "確定", "決定", "OK"]:
            try:
                btn = page.locator(f'button:has-text("{btn_text}")')
                if btn.count() > 0 and btn.first.is_visible():
                    btn.first.click()
                    wait(page, 1000)
                    return True
            except Exception:
                pass

        # 確定ボタンが見つからない場合、Escape で閉じる
        page.keyboard.press("Escape")
        wait(page, 500)
        return True

    except Exception as e:
        print(f"      経路選択失敗: {e} → キャンセルして手動入力")
        try:
            page.locator('button:has-text("キャンセル")').click()
        except Exception:
            page.keyboard.press("Escape")
        wait(page, 500)
        return False


def select_account_item(page: Page):
    """経費科目「交通費（電車在来線・バス）」を選択"""
    try:
        # 経費科目「選択」ボタンをクリック
        sel_btn = page.locator('button.vb-button--small:has-text("選択")').last
        if sel_btn.count() == 0:
            sel_btn = page.locator('button:has-text("選択")').last
        sel_btn.wait_for(timeout=3000)
        sel_btn.click()
        wait(page, 1500)

        # 検索ボックスがあれば「交通費」と入力
        search = page.locator(
            'input[placeholder*="検索"], input[aria-label*="検索"], '
            'input[type="search"], input[placeholder*="科目"]'
        )
        if search.count() > 0:
            search.first.fill("交通費")
            wait(page, 800)

        # 「交通費（電車在来線・バス）」をクリック
        target = page.locator(f'text="{ACCOUNT_ITEM}"')
        if target.count() == 0:
            target = page.locator(f':has-text("{ACCOUNT_ITEM}")')
        target.first.wait_for(timeout=5000)
        target.first.click()
        wait(page, 500)
        print(f"      経費科目: {ACCOUNT_ITEM}")
    except Exception as e:
        print(f"      経費科目の選択をスキップ: {e}")


def add_line_item(page: Page, idx: int, month: int, day: int,
                  from_st: str, to_st: str, amount: int):
    year = 2026
    expense_date = f"{year}/{month:02d}/{day:02d}"
    route = f"{from_st} → {to_st}" if to_st else from_st
    memo = f"{DESCRIPTION}（{route}）"

    print(f"  [{idx+1:02d}/{len(ENTRIES)}] {expense_date}  {route}  ¥{amount:,}")

    # 「手動で経費入力」で新しい申請行を追加
    page.locator('button:has-text("手動で経費入力")').click()
    wait(page, 800)

    # 日付を設定
    date_field = page.locator('input[aria-label="日付"]').last
    date_field.click(click_count=3)
    date_field.type(expense_date)
    date_field.press("Tab")
    wait(page, 300)

    # 交通経路ダイアログで経路を入力（到着駅がある場合）
    route_ok = False
    if to_st:
        route_ok = select_route(page, from_st, to_st, amount)

    # 経路選択失敗またはバスの場合は内容を手動入力
    if not route_ok:
        page.locator('textarea[aria-label="内容"]').last.fill(memo)

    # 金額を設定（経路自動入力でも実際の Suica 金額で上書き）
    wait(page, 300)
    amount_field = page.locator('input[aria-label="金額"]').last
    amount_field.click(click_count=3)
    amount_field.fill(str(amount))
    wait(page, 200)

    # 経費科目を選択
    select_account_item(page)


def save_draft(page: Page):
    print("\n下書き保存中...")
    page.locator('button:has-text("下書き保存")').last.click()
    wait(page, 3000)
    print(f"  保存完了: {page.url}")


def main():
    if not FREEE_EMAIL or not FREEE_PASSWORD:
        print("エラー: .env に FREEE_LOGIN_EMAIL と FREEE_LOGIN_PASSWORD を設定してください。")
        sys.exit(1)

    total = sum(e[4] for e in ENTRIES)
    print(f"=== freee 経費申請 自動入力 ({len(ENTRIES)}件 / ¥{total:,}) ===")
    print("※ブラウザを表示して入力します。入力中は操作しないでください。\n")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=30)

        if os.path.exists(SESSION_FILE):
            print(f"保存済みセッションを読み込みます: {SESSION_FILE}")
            ctx = browser.new_context(
                storage_state=SESSION_FILE,
                locale="ja-JP",
                timezone_id="Asia/Tokyo",
            )
        else:
            ctx = browser.new_context(locale="ja-JP", timezone_id="Asia/Tokyo")

        page = ctx.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})

        try:
            page.goto("https://secure.freee.co.jp", wait_until="domcontentloaded", timeout=60000)
            wait(page, 3000)
            if "login" in page.url or "accounts" in page.url:
                login(page)
                ctx.storage_state(path=SESSION_FILE)
                print(f"  セッションを保存しました: {SESSION_FILE}")
            else:
                print("  freee ログイン済みを確認")

            print("経費精算の新規申請を開いています...")
            page.goto(
                f"https://secure.freee.co.jp/expense_applications/new?company_id={COMPANY_ID}",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            page.wait_for_selector('#input-title', timeout=15000)
            wait(page, 2000)

            # タイトルを設定
            print(f"  タイトル: {TITLE}")
            title_field = page.locator('#input-title')
            title_field.click(click_count=3)
            title_field.fill(TITLE)
            wait(page, 500)

            # 37件の明細を入力
            print(f"\n明細を入力中（{len(ENTRIES)}件）...")
            for i, (month, day, from_st, to_st, amount) in enumerate(ENTRIES):
                add_line_item(page, i, month, day, from_st, to_st, amount)

            save_draft(page)

            print("\n=== 完了 ===")
            print("ブラウザで内容を確認し、問題なければ「申請」ボタンを押してください。")
            print("ブラウザを閉じるまでこのスクリプトは待機します...")
            page.wait_for_timeout(180_000)

        except Exception as e:
            print(f"\nエラー: {e}")
            print("ブラウザで手動確認してください。60秒後に終了します。")
            page.wait_for_timeout(60_000)
        finally:
            ctx.close()
            browser.close()


if __name__ == "__main__":
    main()
