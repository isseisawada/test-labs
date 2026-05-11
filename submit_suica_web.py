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

# ログインセッションを保存するファイル（2回目以降はログイン不要）
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

    # 自動ログインを試みる
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

    # 自動ログイン失敗 or まだログイン画面 → 手動ログインを促す
    if not auto_ok or "login" in page.url or "accounts" in page.url:
        print("\n" + "=" * 60)
        print("【手動ログインが必要です】")
        print("開いているブラウザで freee にログインしてください。")
        print("ログイン完了後、このターミナルで Enter キーを押してください。")
        print("=" * 60)
        input("\nログイン完了したら Enter を押してください... ")
        wait(page, 1000)

    if "login" in page.url or "accounts" in page.url:
        raise RuntimeError("ログインが確認できません。ブラウザでログインしてから再度 Enter を押してください。")

    print("  ログイン成功")


def debug_dump_page(page: Page, label: str = ""):
    """フォーム要素をダンプしてデスクトップに保存"""
    import json
    desk = os.path.expanduser("~/Desktop")
    shot = os.path.join(desk, f"freee_debug_{label}.png")
    page.screenshot(path=shot, full_page=True)
    print(f"  スクリーンショット保存: {shot}")

    elements = page.evaluate("""() => {
        const result = [];
        document.querySelectorAll('input, textarea, select, button').forEach(el => {
            result.push({
                tag: el.tagName,
                type: el.type || '',
                name: el.name || '',
                id: el.id || '',
                placeholder: el.placeholder || '',
                value: el.value || '',
                className: el.className.substring(0, 80),
                ariaLabel: el.getAttribute('aria-label') || '',
                dataTestid: el.getAttribute('data-testid') || '',
                text: el.textContent.trim().substring(0, 40),
                outerHTML: el.outerHTML.substring(0, 200),
            });
        });
        return result;
    }""")

    dump_path = os.path.join(desk, f"freee_debug_{label}.json")
    with open(dump_path, "w", encoding="utf-8") as f:
        json.dump(elements, f, ensure_ascii=False, indent=2)
    print(f"  要素リスト保存: {dump_path}")
    return elements


def open_new_application(page: Page):
    print("経費精算の新規申請を開いています...")
    page.goto(
        f"https://secure.freee.co.jp/expense_applications/new?company_id={COMPANY_ID}",
        wait_until="domcontentloaded",
        timeout=60000,
    )
    # ページ内の何らかの入力要素が出るまで待つ
    try:
        page.wait_for_selector('input, textarea, select', timeout=15000)
    except PWTimeout:
        pass
    wait(page, 3000)


def set_title(page: Page):
    print(f"  タイトルを設定: {TITLE}")
    title_sel = 'input[name*="title"], input[placeholder*="タイトル"], input[id*="title"]'
    page.fill(title_sel, TITLE)
    wait(page)


def select_form_template(page: Page):
    """申請フォーム（【部長以上：支払申請】経理承認）を選択"""
    print("  申請フォームを選択中...")
    try:
        form_sel = 'select[name*="template"], select[id*="template"], [data-testid*="template"]'
        if page.locator(form_sel).count() > 0:
            page.select_option(form_sel, label="【部長以上：支払申請】経理承認")
            wait(page, 1500)
            return
        page.click('text=【部長以上：支払申請】経理承認')
        wait(page, 1500)
    except Exception:
        print("  申請フォーム選択をスキップ（自動選択済みか手動で対応）")


def select_department(page: Page):
    """部門を選択（最初の選択肢を使用）"""
    print("  部門を選択中...")
    try:
        dept_sel = 'select[name*="section"], select[id*="section"], select[name*="department"]'
        opts = page.locator(dept_sel)
        if opts.count() > 0:
            page.evaluate("""(sel) => {
                const el = document.querySelector(sel);
                if (el) {
                    for (let i = 0; i < el.options.length; i++) {
                        if (el.options[i].value) {
                            el.selectedIndex = i;
                            el.dispatchEvent(new Event('change', {bubbles: true}));
                            break;
                        }
                    }
                }
            }""", dept_sel)
            wait(page, 1000)
    except Exception as e:
        print(f"  部門選択スキップ: {e}")


def add_line_item(page: Page, idx: int, month: int, day: int,
                  from_st: str, to_st: str, amount: int):
    """明細1行を入力する"""
    year = 2026
    expense_date = f"{year}/{month:02d}/{day:02d}"
    route = f"{from_st} → {to_st}" if to_st else from_st
    memo = f"{DESCRIPTION}（{route}）"

    print(f"  [{idx+1:02d}/37] {expense_date}  {route}  ¥{amount:,}")

    if idx > 0:
        add_btn_selectors = [
            'button:has-text("行を追加")',
            'button:has-text("明細を追加")',
            'button:has-text("+ 行")',
            '[data-testid*="add-line"]',
            'a:has-text("行を追加")',
        ]
        for sel in add_btn_selectors:
            try:
                if page.locator(sel).count() > 0:
                    page.locator(sel).last.click()
                    wait(page, 600)
                    break
            except Exception:
                continue

    rows = page.locator('tr[class*="line"], .expense-line, [data-testid*="line-row"], tbody tr').all()
    row = rows[-1] if rows else page

    def fill_in_row(field_sel: str, value: str):
        try:
            targets = row.locator(field_sel) if rows else page.locator(field_sel)
            if targets.count() > 0:
                targets.last.fill(value)
                return True
        except Exception:
            pass
        try:
            all_targets = page.locator(field_sel)
            if all_targets.count() > 0:
                all_targets.nth(all_targets.count() - 1).fill(value)
                return True
        except Exception:
            pass
        return False

    fill_in_row('input[name*="date"], input[placeholder*="日付"], input[type="date"]', expense_date)
    wait(page, 200)

    fill_in_row('input[name*="amount"], input[placeholder*="金額"]', str(amount))
    wait(page, 200)

    fill_in_row('input[name*="description"], input[name*="memo"], input[placeholder*="内容"], textarea[name*="description"]', memo)
    wait(page, 200)


def save_draft(page: Page):
    """下書き保存"""
    print("\n下書き保存中...")
    draft_selectors = [
        'button:has-text("下書き保存")',
        'button:has-text("一時保存")',
        'input[value*="下書き"]',
        'a:has-text("下書き保存")',
    ]
    for sel in draft_selectors:
        try:
            if page.locator(sel).count() > 0:
                page.locator(sel).click()
                wait(page, 3000)
                print(f"  保存完了: {page.url}")
                return
        except Exception:
            continue
    print("  下書き保存ボタンが見つかりませんでした。手動で保存してください。")


def main():
    if not FREEE_EMAIL or not FREEE_PASSWORD:
        print("エラー: .env に FREEE_LOGIN_EMAIL と FREEE_LOGIN_PASSWORD を設定してください。")
        sys.exit(1)

    total = sum(e[4] for e in ENTRIES)
    print(f"=== freee 経費申請 自動入力 ({len(ENTRIES)}件 / ¥{total:,}) ===")
    print("※ブラウザを表示して入力します。入力中は操作しないでください。\n")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=50)

        # 保存済みセッションがあれば読み込む（再ログイン不要）
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
            # ログイン確認（未ログインなら自動ログイン）
            page.goto("https://secure.freee.co.jp", wait_until="domcontentloaded", timeout=60000)
            wait(page, 3000)
            if "login" in page.url or "accounts" in page.url:
                login(page)
                # セッションを保存（次回以降はログイン不要）
                ctx.storage_state(path=SESSION_FILE)
                print(f"  セッションを保存しました: {SESSION_FILE}")
            else:
                print("  freee ログイン済みを確認")

            open_new_application(page)

            # タイトルを設定（正しいセレクタ判明）
            print(f"  タイトルを設定: {TITLE}")
            page.fill('#input-title', TITLE)
            wait(page)

            # 「手動で経費入力」をクリックして1行目の入力欄を出す
            print("  「手動で経費入力」をクリック...")
            page.click('button.vb-button--appearanceTertiary:has-text("手動で経費入力")')
            wait(page, 2000)

            # クリック後のフォーム構造を調査
            print("\n【デバッグ】手動入力後のフォーム構造を調査中...")
            debug_dump_page(page, "after_manual")
            print("デスクトップの freee_debug_after_manual.png と .json を確認してください。")
            print("スクリプトを終了します。")
            return

            save_draft(page)

            print("\n=== 完了 ===")
            print("ブラウザで内容を確認し、問題なければ「申請」ボタンを押してください。")
            print("ブラウザを閉じるまでこのスクリプトは待機します...")
            page.wait_for_timeout(120_000)  # 2分間ブラウザを開いたまま

        except Exception as e:
            print(f"\nエラー: {e}")
            print("ブラウザで手動確認してください。60秒後に終了します。")
            page.wait_for_timeout(60_000)
        finally:
            ctx.close()
            browser.close()


if __name__ == "__main__":
    main()
