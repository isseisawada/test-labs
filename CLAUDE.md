# test-labs

python-pptx を使って PowerPoint 提案書を生成するプロジェクト。

## 主なファイル

- `yadokari_proposal.py` - 最初のバージョン
- `yadokari_proposal_v3.py` - v3
- `yadokari_proposal_v4.py` - v4（最新）

## 実行方法

```bash
python yadokari_proposal_v4.py   # 最新バージョンを実行して pptx を生成
```

## 依存ライブラリ

- `python-pptx`
- `lxml`

## コードスタイル

- スライドレイアウトは `BLANK`（index 6）を使用
- 座標・サイズは `Inches()` 単位で指定
- ヘルパー関数（`S()`, `bg()`, `rect()`, `tb()` など）を積極的に使う
