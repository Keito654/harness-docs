# harness-docs

Claude Code 向けのエージェントファーストなドキュメント管理プラグインです。OpenAI の *Harness Engineering* パターンに基づいた2つのスキルを提供します。

## スキル一覧

### `/harness-docs:harness-docs` — ドキュメント体系の構築

既存のリポジトリを解析し、エージェント（Claude Code・Codex・Cursor など）が迷わず動ける `docs/` 体系を自動生成します。

**こんなときに使う:**
- 「このリポジトリのドキュメントを整備したい」
- 「AGENTS.md / CLAUDE.md を作りたい」
- 「アーキテクチャを文書化したい」
- 「コーディングエージェントが参照できる設計ドキュメントを用意したい」

**生成物:**
- `AGENTS.md` — エージェント向けの短いエントリーポイント（〜100行）
- `ARCHITECTURE.md` — ドメインとレイヤーの全体マップ
- `docs/design-docs/` — コア設計ドキュメント群
- `docs/exec-plans/` — 実行計画・技術的負債トラッカー
- `docs/PLANS.md`, `docs/QUALITY_SCORE.md` など

### `/harness-docs:doc-gardener` — ドキュメントの鮮度維持

既存の `docs/` をスキャンし、コードや git 履歴と照合してドリフト（陳腐化）を検出・修正します。

**こんなときに使う:**
- 「ドキュメントが古くなってきた、更新してほしい」
- 「大きなリファクタリングをした後、どのドキュメントが影響を受けるか確認したい」
- 「docs とコードがずれていないかチェックしたい」
- 「定期的なドキュメント整備（doc gardening）を実行したい」

**出力:**
- **ドリフトレポート** — 各ドキュメントの鮮度評価（🔴 Critical / 🟠 Likely stale / 🟡 Possibly stale / 🟢 Fresh）と根拠（コードの場所・git コミット）
- **承認ベースの更新** — レポートを確認してからユーザーが承認した箇所だけを修正

## インストール

```shell
# Step 1: マーケットプレイスとして追加
/plugin marketplace add keito654/harness-docs

# Step 2: プラグインをインストール
/plugin install harness-docs@harness-docs
```

### ローカル開発・テスト

```bash
git clone https://github.com/keito654/harness-docs
claude --plugin-dir ./harness-docs
```

## 使い方

インストール後、Claude Code のセッション内でスキルを呼び出します。

```
# ドキュメント体系を一から構築する
/harness-docs:harness-docs

# 既存ドキュメントの鮮度チェックと更新
/harness-docs:doc-gardener
```

引数なしで実行すると、スキルが現在のリポジトリを解析して適切に進めます。

## スキルの設計思想

両スキルは以下の原則を共有しています。

1. **ドリフトはバグ** — コードと食い違うドキュメントは、ドキュメントがない状態より有害。エージェントが誤った情報をもとに行動するため。
2. **証拠ベース** — 「古い」と判断するには、コードの場所や git コミットを必ず根拠として示す。感覚で flagging しない。
3. **プログレッシブ・ディスクロージャー** — エントリーポイントは短く保ち（〜100行）、詳細は `docs/` 以下の深いドキュメントに委ねる。
4. **機械的な検証可能性** — lint や CI で鮮度・クロスリンク・オーナーシップを自動チェックできる構造にする。

## 付属ツール

`doc-gardener` スキルには `scripts/docs_lint.py` が同梱されています。このスクリプトは以下を自動検出します：

- メタデータの欠損・不正（`Status`・`Last reviewed` ヘッダー）
- 壊れた内部リンク
- コードフェンス内のパス参照が実在するか
- `docs/` インデックスのカバレッジギャップ
- `Last reviewed` から N 日以上経過したドキュメント（デフォルト 60 日）

```bash
python3 skills/doc-gardener/scripts/docs_lint.py --root . --threshold-days 60 --json
```

## ライセンス

MIT

## 関連リソース

- [OpenAI Harness Engineering 記事](https://openai.com/index/harness-engineering/) — このプラグインの設計思想の源泉
