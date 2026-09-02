# CLAUDE.md — freee 経費精算 プロジェクトルール

このファイルは Claude Code が経費精算の自動化を扱うときに参照するルール集。
新しいルールが決まったら都度追記する。

## freee API 設定

- **承認経路 ID (API 用)**: `1469199`（申請フォーム名: **経費精算_API用（さわだ指定）**）
- **会社ID**: `845775` (YADOKARI株式会社)
- **OAuth アプリ**: 「経理用（mcp）」（Client ID: `732296596197183`）
  - コールバック URL: `http://127.0.0.1:54321/callback`
  - 権限: [会計] 経費精算・経費科目・各種申請・ファイルボックス・部門・取引 の参照＋更新
  - 認可 URL には `scope` を付けない（`prompt=select_company` を付ける）
  - 認可は **澤田さんの freee アカウントでログインしているブラウザ** で行う（別アカウントだと「アプリが存在しない」）
- **明細テンプレート ID** (freee 側で確認済み):
  - 289807: 交通費（電車在来線・バス）
  - 300519: 交通費（特急・新幹線）
  - 300520: 交通費（タクシー）
  - 300524: ガソリン代
  - 300525: 駐車場代
  - 300528: 会議費（社内）
  - 300529: 会議費（社外）
  - 300530: 接待交際費（一人税込10,000円以下）
  - 300531: 接待交際費（一人税込10,000円超）
  - 300535: 備品消耗品（事務用品等）
- **勘定科目 ID**: 雑費 = `134321784`（テンプレートが無いので明細行の `account_item_id` で上書きする）
- **API の明細形式**: `purchase_lines[] > {transaction_date, receipt_id, sub_receipt_ids, expense_application_lines[] > {description, amount, expense_application_line_template_id, account_item_id}}`
  - `receipt_id` = 領収書、`sub_receipt_ids` = 補足資料（Suica 一覧など）
  - 交通経路検索（「交通経路を選択」）は公式 API に無い（UI 専用）。description に「打ち合わせ（駅 → 駅）」を書く運用

## 申請の分け方（月次ルール）

**2026年8月分以降（`submit_expenses.py` が自動でこの分け方をする）:**
- **電車の交通費（Suica）は独立した申請にまとめる**
  - 申請1: Suica 交通費のみ（テンプレート 289807）
  - 申請2以降: 領収書系（会議費・接待交際費・雑費・タクシー等）
- タイトル形式: `経費精算申請X/N`（Suica 申請 → 領収書申請の順で通し番号）
- 30件ずつバッチ分割
- **Suica 一覧のスクショ/PDF は Suica 申請の申請行1に補足資料（sub_receipt_ids）として添付**
- 領収書申請の備考: `電車交通費は申請Xにまとめています。`

## 勘定科目（ベンダー・キーワード → テンプレートID）

デフォルトのマッピング（`submit_expenses.py` の `decide()`）:
- Suica → 289807 交通費（電車在来線・バス）
- GO タクシー → 300520 交通費（タクシー）
- 東日本旅客鉄道 / JR / 新幹線 → 300519 交通費（特急・新幹線）
- 石油・SS・ガソリン → 300524 ガソリン代
- ○○パーク / 駐車場 / パーキング → 300525 駐車場代
- STATION WORK → 300528 会議費（社内）、内容は `オフィスブース利用（STATION WORK 東京駅）`
- Soil work / Staple → **雑費**（テンプレート 300535 + `account_item_id=134321784` で上書き）
- Google Cloud / Apple / NewsPicks → **雑費**（同上）
- **note株式会社（サブスク） → 雑費**（同上）

### 雑費の実装
freee には「雑費」テンプレートは存在しないが、`account_item_id=134321784` (雑費) を
明細行に指定するとテンプレート既定の勘定科目を上書きできる。
`submit_expenses.py` の `T_SUPPLY + A_MISC` 組み合わせがこれを実現。

### 会議費 / 接待交際費 の判定ルール

**金額ベースで一次判定（重要）:**
- **飲食代（食事・カフェ・懇親会等）が ¥5,000 以下** → 会議費
- **飲食代が ¥5,000 超** → **すべて接待交際費**（会議費にしない）

**会議費（¥5,000以下）の内訳:**
- 社内メンバーのみ → 会議費（社内）
- 社外含む（entries.json で `"external": true`）→ 会議費（社外）

**接待交際費（¥5,000超）の内訳:**
- **一人あたり合計金額 = 合計金額 ÷ 参加人数（澤田含む）**
  - entries.json の `participants`（澤田を除く名前リスト）から人数 = len+1 を自動計算。`people` で上書き可
- 一人税込 ¥10,000 以下 → 接待交際費（一人税込10,000円以下）
- 一人税込 ¥10,000 超 → 接待交際費（一人税込10,000円超）
- 参加者未記入だと一人あたり判定ができないので、ドライランで ⚠ が出る → entries.json を埋めてから本番実行

**参加者記載（重要）:**
- **会議費・接待交際費の両方とも 参加者フルネームを内容欄に必ず記載**
- 例: `打ち合わせ（店名）きたもと・えんどう・ごう`（ひらがなフルネームでOK）
- 社外者は所属も明記: `三井不動産なかむらしょうご`
- 株主同席時: 末尾に `株主XX親睦のため`（entries.json の `shareholder`）

### 説明文フォーマット
- Suica: `打ち合わせ（駅名 → 駅名）`
- タクシー: `タクシー利用（乗車地→降車地）`
- 会議費（社内）: `オフィスブース利用（STATION WORK 東京駅）` / `打ち合わせ（店名）参加者`
- 接待交際費: `打ち合わせ（店名）参加者フルネーム列挙`（フルネームひらがな可）
- 株主同席時: 末尾に `株主XXX親睦のため` を追加
- サブスク系: `月刊 谷尻誠 購読料　株主たにじりまこと親睦のため` のように定期購読・株主関係を明記

### entries.json（領収書エントリ）で使うフィールド
```json
{
  "date": "2026-08-15", "kind": "receipt", "vendor": "鮨処秋田家", "amount": 25839,
  "account": "接待交際費",
  "description": "打ち合わせ（鮨処秋田家）",
  "participants": ["きたもと", "えんどう", "ごう"],
  "people": 4,
  "external": false,
  "shareholder": "",
  "receipt_path": "inputs_202608/receipts/xxx.jpg"
}
```
- `participants` / `external` / `shareholder` / `people` は OCR では埋まらない。**merge 後に手で入れる**
- `merge_entries.py` を再実行しても、既存 entries.json の手修正（上記フィールド + description/account/date/amount）は `receipt_path` キーで引き継がれる

## 領収書アップロード

- `POST /api/1/receipts` は「経理用（mcp）」のトークン + ファイルボックス権限で動く
- entries.json の各エントリに `receipt_path` を入れておくと `submit_expenses.py` が自動アップロード＆添付
- 登録後に添付し直す場合は `attach_receipts_later.py`（申請IDとバッチ範囲を書き換えて使う）

## OCR

- Suica スクリーンショット・PDF → `extract_suica_screenshots.py --month M`（Claude Vision）
- 領収書写真・PDF → `extract_receipts.py --month M`（Claude Vision）
- 統合 → `merge_entries.py --month M`（GO日付補正、年誤読補正、勘定科目補正、手修正引き継ぎ）
- 登録 → `submit_expenses.py --month M`（Suica/領収書の申請分割、テンプレートID決定、領収書・補足資料アップロード、freee API 登録）
- `submit_july_2026.py` は7月分の履歴として残してあるだけ（今後は使わない）

## 月次ワークフロー（8月分以降、毎月使えるテンプレ）

### 事前に用意するもの

**画像・書類系（Mac に保存）**
- Suica 利用履歴のスクリーンショット or PDF（1〜31日全部映るように。前月分が混ざっても可、後で除外）
- 現金領収書の写真・PDF（レシート・スタバなど紙ベース）
- Web サービス領収書:
  - GO タクシー領収書（アプリ or メールから DL。ファイル名 `GO領収書_YYYYMMDD_HHMM.pdf` だと日付を自動補正）
  - STATION WORK 領収書（サイトからDL）
  - note 領収書（アカウント > 領収書からDL）
  - Newspicks (Apple サブスク) 領収書（メールに来る Apple 領収書）
  - Google Cloud 請求書 (メール or GCP コンソール)
  - Soil work / Staple の請求書
  - その他 定期購読・出張系（新幹線の領収書は乗車日を entries.json で直す）
- **会食・打ち合わせの参加者名メモ**（店名ごとに誰と何人か。これが無いと接待交際費の判定ができない）

**環境変数（`.env` に既に入っているはず、無ければ）**
```
FREEE_CLIENT_ID=732296596197183          # 経理用（mcp）
FREEE_CLIENT_SECRET=xxxxxxxx             # freee 開発者ページで確認
FREEE_ACCESS_TOKEN=xxxxxxxx              # 期限切れなら python3 -m freee_expense.auth
FREEE_REFRESH_TOKEN=xxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxx          # Vision OCR 用
FREEE_LOGIN_EMAIL=sawada@yadokari.net
```

### 実行手順（コピペ用・8月分の例）

**Step 0: 最新コードを取得**
```bash
cd /Users/issei/Applications/Claude/test-labs-git
git pull origin claude/freee-expense-submission-fYEOe
```

**Step 1: 画像配置**（ディレクトリは git に入っている）
```
inputs_202608/suica/         ← Suica 履歴のスクショ/PDF
inputs_202608/receipts/      ← 手元で写真を撮った紙の領収書
inputs_202608/web_receipts/  ← オンラインで取得した領収書（GO / STATION WORK / note / Apple / Google Cloud / Staple 等の PDF）
```
- `extract_receipts.py` は receipts/ と web_receipts/ の両方を読む（分け方は整理用で、処理は同じ）

**Step 2: OCR で抽出**
```bash
python3 extract_suica_screenshots.py --month 8   # → inputs_202608/entries_suica.json
python3 extract_receipts.py --month 8            # → inputs_202608/entries_receipts.json
```

**Step 3: マージして entries.json 生成**
```bash
python3 merge_entries.py --month 8               # → inputs_202608/entries.json
```
- 件数・合計を確認。対象月外の行、誤読（年・金額・店名）があれば `inputs_202608/entries.json` を直接修正
- **会議費・接待交際費の行に `participants`（と必要なら `external` / `shareholder`）を入れる**
- 新幹線・JR の領収書は `date` を実際の乗車日に直す

**Step 4: ドライラン（送信前確認）**
```bash
python3 submit_expenses.py --month 8 --dry-run
```
- 申請の分かれ方（Suica 申請 → 領収書申請）と各行のラベルを確認
  - `[電車・バス]` `[タクシー]` `[会議費(社内)]` `[接待交際費(一人¥x・10000以下)]` `[雑費]` など
- 末尾の「⚠ 要確認」が 0 件になるまで entries.json を直して再ドライラン

**Step 5: 本番実行（freee に下書き登録）**
```bash
python3 submit_expenses.py --month 8
```
- 領収書と Suica 一覧をアップロード → 申請作成 → 最後に各申請の URL が出る

**Step 6: freee UI で内容確認 → 申請ボタン**
- `https://secure.freee.co.jp/expense_applications_v2/{申請ID}`
- 確認ポイント: 経費科目 / 参加者名 / 領収書の 📎 / Suica 申請の補足資料 / 備考
- OK なら各申請で「申請」を押して承認フローに送出

### トラブル時の対処

| 症状 | 原因 | 対処 |
|---|---|---|
| 「ページが見つかりません」「アプリが存在しない」（認可時） | Client ID 誤り or 別アカウントでログイン中 | `.env` の FREEE_CLIENT_ID を `732296596197183` に。URL を澤田アカウントでログイン済みのブラウザ（or シークレット）に貼る |
| 401 / トークン期限切れ | アクセストークンは6時間。リフレッシュ失敗時 | `python3 -m freee_expense.auth` で再認可 |
| 403 Forbidden (receipts) | トークンが古いスコープ | 再認可（上記） |
| 400 明細行を入力してください | 明細形式が旧式 | client.py が line_template_id のネスト形式か確認 |
| 400 sub_receipt_ids 関連 | 補足資料の項目名が変わった | `--no-suica-attach` で登録し、Suica 一覧は UI から手動添付 |
| git push 403 | リポジトリ名変更（test-labs → yadokari-labs） | 時間を置いて再試行、または `git remote set-url origin https://github.com/isseisawada/yadokari-labs.git` |

### 事後（申請確定後）

- Client Secret 保管確認（1Password 等）。チャットに貼った Secret は再生成して無効化する
- 新しいルール/勘定科目マッピング変更があれば CLAUDE.md に追記
- 次月分: 翌月頭に本ワークフロー実施（`--month 9`）

### 効率化のコツ

- Suica は月末に一気にスクショ or CSV DL しておく
- 現金領収書は撮り溜め（会食後すぐ）→ 月末フォルダに集約。**会食は誰と何人かをその場でメモ**
- Web サービスの領収書メールは Gmail ラベル「経費」等でフィルタリング
- 月末までに inputs_2026MM を揃えておく → 翌月1日に一気実行
- Vision OCR は API 費用が少しかかる（数百円/月）ので、精度悪ければ entries.json を手動修正した方が早い
