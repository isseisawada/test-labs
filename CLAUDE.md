# CLAUDE.md — freee 経費精算 プロジェクトルール

このファイルは Claude Code が経費精算の自動化を扱うときに参照するルール集。
新しいルールが決まったら都度追記する。

## freee API 設定

- **承認経路 ID (API 用)**: `1469199`（申請フォーム名: **経費精算_API用（さわだ指定）**）
- **会社ID**: `845775` (YADOKARI株式会社)
- **OAuth アプリ**: 「経理用（mcp）」（Client ID: `732296596197183`）
  - コールバック URL: `http://127.0.0.1:54321/callback`
  - 権限: [会計] 経費精算・経費科目・各種申請・ファイルボックス・部門・取引 の参照＋更新
- **明細テンプレート ID** (freee 側で確認済み):
  - 289807: 交通費（電車在来線・バス）
  - 300519: 交通費（特急・新幹線）
  - 300520: 交通費（タクシー）
  - 300524: ガソリン代
  - 300525: 駐車場代
  - 300528: 会議費（社内）
  - 300529: 会議費（社外）
  - 300530: 接待交際費（一人5000円以下）
  - 300531: 接待交際費（一人5000円超）
  - 300535: 備品消耗品（事務用品等）

## 申請の分け方（月次ルール）

**2026年8月分以降:**
- **電車の交通費（Suica）は独立した申請にまとめる**
  - 申請1: Suica 交通費のみ（テンプレート 289807）
  - 申請2以降: 領収書系（会議費・接待交際費・雑費・タクシー等）
- タイトル形式: `経費精算申請X/N`
- 30件ずつバッチ分割
- **Suica 一覧の PDF/画像は 領収書申請の備考欄に添付**
- **備考欄**: `電車交通費は申請Xにsuicaの乗車一覧を添付しています。` の記載を推奨

## 勘定科目（ベンダー・キーワード → テンプレートID）

デフォルトのマッピング:
- Suica → 289807 交通費（電車在来線・バス）
- GO タクシー → 300520 交通費（タクシー）
- 東日本旅客鉄道 / JR / 新幹線 → 300519 交通費（特急・新幹線）
- 石油・SS・ガソリン → 300524 ガソリン代
- ○○パーク / 駐車場 / パーキング → 300525 駐車場代
- STATION WORK → 300528 会議費（社内）
- Soil work / Staple → **雑費**（テンプレート 300535 + `account_item_id=134321784` で上書き）
- Google Cloud / Apple / NewsPicks → **雑費**（同上、テンプレート 300535 + 雑費上書き）
- **note株式会社（サブスク） → 雑費**（同上）

### 雑費の実装
freee には「雑費」テンプレートは存在しないが、`account_item_id=134321784` (雑費) を
明細行に指定するとテンプレート既定の勘定科目を上書きできる。
`submit_july_2026.py` の `T_SUPPLY + A_MISC` 組み合わせがこれを実現。

### 会議費 / 接待交際費 の判定ルール

**金額ベースで一次判定（重要）:**
- **飲食代（食事・カフェ・懇親会等）が ¥5,000 以下** → 会議費
- **飲食代が ¥5,000 超** → **すべて接待交際費**（会議費にしない）

**会議費（¥5,000以下）の内訳:**
- 社内メンバーのみ → 会議費（社内）
- 社外含む → 会議費（社外）

**接待交際費（¥5,000超）の内訳:**
- **一人あたり合計金額 = 合計金額 ÷ 参加人数（澤田含む）**
- 一人税込 ¥10,000 以下 → 接待交際費（一人税込10,000円以下）
- 一人税込 ¥10,000 超 → 接待交際費（一人税込10,000円超）

**参加者記載（重要）:**
- **会議費・接待交際費の両方とも 参加者フルネームを内容欄に必ず記載**
- 例: `打ち合わせ（店名）きたもと・えんどう・ごう`（ひらがなフルネームでOK）
- 社外者は所属も明記: `三井不動産なかむらしょうご`
- 株主同席時: 末尾に `株主XX親睦のため`

### 説明文フォーマット
- Suica: `打ち合わせ（駅名 → 駅名）`
- タクシー: `タクシー利用（乗車地→降車地）`
- 会議費（社内）: `オフィスブース利用（STATION WORK 東京駅）` / `打ち合わせ（店名）`
- 接待交際費: `打ち合わせ（店名）参加者フルネーム列挙`（フルネームひらがな可）
- 株主同席時: 末尾に `株主XXX親睦のため` を追加
- サブスク系: `月刊 谷尻誠 購読料　株主たにじりまこと親睦のため` のように定期購読・株主関係を明記

## 領収書アップロード

- `POST /api/1/receipts` は「経理用（mcp）」のトークン + ファイルボックス権限で動く
- entries.json の各エントリに `receipt_path` を入れておくと `submit_july_2026.py` / `attach_receipts_later.py` で自動アップロード＆添付

## OCR

- Suica スクリーンショット・PDF → `extract_suica_screenshots.py`（Claude Vision）
- 領収書写真・PDF → `extract_receipts.py`（Claude Vision）
- 統合 → `merge_entries.py`（GO日付補正、2014→2026補正、勘定科目補正）
- 登録 → `submit_YYYY_MM.py`（バッチ分割、テンプレートID決定、領収書アップロード、freee API 登録）

## 月次ワークフロー（8月分以降、毎月使えるテンプレ）

### 事前に用意するもの

**画像・書類系（Mac に保存）**
- Suica 利用履歴のスクリーンショット or PDF（1〜31日全部映るように）
- 現金領収書の写真・PDF（レシート・スタバなど紙ベース）
- Web サービス領収書:
  - GO タクシー領収書（アプリ or メールから DL）
  - STATION WORK 領収書（サイトからDL）
  - note 領収書（アカウント > 領収書からDL）
  - Newspicks (Apple サブスク) 領収書（メールに来る Apple 領収書）
  - Google Cloud 請求書 (メール or GCP コンソール)
  - Soil work / Staple の請求書
  - その他 定期購読・出張系

**環境変数（`.env` に既に入っているはず、無ければ）**
```
FREEE_CLIENT_ID=732296596197183          # 経理用（mcp）
FREEE_CLIENT_SECRET=xxxxxxxx             # freee 開発者ページで確認
FREEE_ACCESS_TOKEN=xxxxxxxx              # 期限切れなら python3 -m freee_expense.auth
FREEE_REFRESH_TOKEN=xxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxx          # Vision OCR 用
FREEE_LOGIN_EMAIL=sawada@yadokari.net
```

### 実行手順（コピペ用）

**Step 1: 8月分ディレクトリ作成 & 画像配置**
```bash
cd /Users/issei/Applications/Claude/test-labs-git
mkdir -p inputs_202608/{suica,receipts,web_receipts}

# Suica 履歴のスクショ/PDF を inputs_202608/suica/ に入れる
# 現金領収書・Webサービス領収書 を inputs_202608/receipts/ に入れる
```

**Step 2: 新規登録スクリプトを作成（7月版をコピー）**
```bash
cp submit_july_2026.py submit_august_2026.py
# submit_august_2026.py 内の以下を書き換え:
#   MONTH = 8
#   INPUT_FILE = ... "inputs_202608"
# 同じ要領で extract_suica_screenshots.py と extract_receipts.py の
# INPUT_DIR / OUTPUT 変数も 202608 に変更（sed でも可）
sed -i '' 's|inputs_202607|inputs_202608|g' extract_suica_screenshots.py extract_receipts.py merge_entries.py submit_august_2026.py
sed -i '' 's|MONTH *= *7|MONTH = 8|' submit_august_2026.py
```

**Step 3: OCR で抽出**
```bash
python3 extract_suica_screenshots.py    # → inputs_202608/entries_suica.json
python3 extract_receipts.py             # → inputs_202608/entries_receipts.json
```

**Step 4: マージして entries.json 生成**
```bash
python3 merge_entries.py                # → inputs_202608/entries.json
```
- 統合結果と件数を確認
- 誤読があれば `inputs_202608/entries.json` を直接エディタで修正

**Step 5: ドライラン（送信前確認）**
```bash
python3 submit_august_2026.py --dry-run
```
- 各行のラベル `[電車・バス]`, `[タクシー]`, `[会議費(社内)]`, `[接待交際費(10000以下)]`, `[雑費(=消耗品テンプレ+雑費上書き)]` を確認
- 参加者フルネームが descriptionに入っているか確認（会議費・接待交際費）
- 誤りがあれば entries.json を直して再ドライラン

**Step 6: 申請分けルールに従い、Suica と 領収書系を分離**
- 8月以降ルール: **Suica は独立申請、領収書系は別申請**
- entries.json を Suica系（kind="suica"）と 領収書系（kind!="suica"）で 2 ファイルに分割するか、
  現行スクリプトのバッチ分けを月次でカスタムする

**Step 7: 本番実行（freee 登録）**
```bash
python3 submit_august_2026.py
```
- 領収書アップロード（`/api/1/receipts`）
- 申請作成（`/api/1/expense_applications` with approval_flow_route_id=1469199）
- 申請ID が出力される

**Step 8: freee UI で内容確認**
- 各申請URL:
  ```
  https://secure.freee.co.jp/expense_applications_v2/{申請ID}
  ```
- 確認ポイント:
  - 経費科目が正しいか（雑費、会議費、接待交際費）
  - 参加者名が入っているか
  - 領収書が明細に紐付いているか（📎 マーク）
  - 備考欄: Suica 一覧の補足資料を添付、`電車交通費は申請Xにsuicaの乗車一覧を添付しています。` と記載

**Step 9: 申請ボタン押下**
- 内容 OK なら freee UI で「申請」ボタンを押して承認フローに送出

### トラブル時の対処

| 症状 | 原因 | 対処 |
|---|---|---|
| ページが見つかりません | OAuth Client ID 誤り | `.env` の FREEE_CLIENT_ID を経理用(mcp) = `732296596197183` に |
| 403 Forbidden (receipts) | 権限 or トークン古い | `python3 -m freee_expense.auth` で再認可 |
| 400 明細行を入力してください | 明細形式が旧式 | client.py で line_template_id を使うネスト形式か確認 |
| 「アプリが存在しない」 | ログイン中のアカウント違い | Chrome の freee ログインを 澤田さん のアカウントに切替 |
| トークン期限切れ | 6時間で自動リフレッシュ | 期限切れなら `python3 -m freee_expense.auth` |

### 事後（申請確定後）

- Client Secret 保管確認（1Password 等）
- 次月分の予定管理: 8月なら 9月頭に本ワークフロー実施
- 新しいルール/勘定科目マッピング変更があれば CLAUDE.md に追記

### 効率化のコツ

- Suica は月末に一気にスクショ or CSV DL しておく
- 現金領収書は撮り溜め（会食後すぐ）→ 月末フォルダに集約
- Web サービスの領収書メールは Gmail ラベル「経費」等でフィルタリング
- 8月の領収書は 8/31 までにフォルダに揃えておく → 9/1 に一気実行
- Vision OCR は API 費用が少しかかる（数百円/月）ので、精度悪ければ entries.json を手動修正した方が早い
