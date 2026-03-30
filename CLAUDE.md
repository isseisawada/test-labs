# test-labs

python-pptx を使って PowerPoint 提案書を生成するプロジェクト。

## セットアップ

```bash
pip install python-pptx lxml
```

## バージョン履歴

- `yadokari_proposal.py` - v1（原型）
- `yadokari_proposal_v3.py` - v3（ブランド追加）
- `yadokari_proposal_v4.py` - v4（最終版・通常はこれを編集する）

## 実行方法

```bash
python3 yadokari_proposal_v4.py   # 実行すると pptx をリポジトリ直下に生成する
```

## 出力

- 生成された `.pptx` ファイルは git 管理しない

## コードスタイル

- スライドレイアウトは `BLANK`（index 6）を使用
- 座標・サイズは `Inches()` 単位で指定
- ヘルパー関数（`S()`, `bg()`, `rect()`, `tb()` など）を積極的に使う
