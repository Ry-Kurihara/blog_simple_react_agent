# Fishing MCP テストガイド

このディレクトリには、Fishing MCPサーバーのテストコードが含まれています。

## 目次

- [テストの実行方法](#テストの実行方法)
- [テストファイルの構成](#テストファイルの構成)
- [テスト追加のポリシー](#テスト追加のポリシー)
- [TDD（テスト駆動開発）のアプローチ](#tddテスト駆動開発のアプローチ)
- [トラブルシューティング](#トラブルシューティング)

---

## テストの実行方法

### 前提条件

```bash
# fishing_mcpディレクトリに移動
cd server/fishing_mcp

# 仮想環境がアクティブになっていることを確認
# プロジェクトルートで仮想環境を使用している場合
source ../../.venv/bin/activate  # または適切なパス
```

### 全テストの実行

```bash
# すべてのテストを実行
python -m pytest tests/ -v

# カバレッジ付きで実行
python -m pytest tests/ -v --cov=src --cov-report=html
```

### 特定のテストファイルの実行

```bash
# 日付範囲バリデーションのテスト（推奨）
python -m pytest tests/test_date_range_validation.py -v

# 手動確認用スクリプト
python tests/test_manual_validation.py
```

### 特定のテストクラス・メソッドの実行

```bash
# 特定のテストクラスのみ
python -m pytest tests/test_date_range_validation.py::TestValidateDateRange -v

# 特定のテストメソッドのみ
python -m pytest tests/test_date_range_validation.py::TestValidateDateRange::test_16_days_ahead_is_valid -v
```

### 詳細な出力

```bash
# より詳細な出力（print文も表示）
python -m pytest tests/ -v -s

# 失敗したテストのみ再実行
python -m pytest tests/ --lf
```

---

## テストファイルの構成

### `test_date_range_validation.py` ⭐️ メイン

**目的**: 日付範囲検証機能のテスト（現在の実装に対応）

**対象モジュール**: `src/date_utils.py`
- `validate_date_range()`
- `validate_and_check_date()`
- `validate_and_check_datetime()`

**テストケース数**: 17個

**カバレッジ**:
- ✅ 正常ケース: 本日、明日、16日先（境界値）
- ✅ 異常ケース: 過去の日付、17日先、遥か未来
- ✅ 実際のシナリオ: 2026-11-29（問題のケース）

**実行方法**:
```bash
python -m pytest tests/test_date_range_validation.py -v
```

---

### `test_manual_validation.py` 🔧 手動確認用

**目的**: 手動でdate_utilsの動作を確認するための簡易スクリプト

**実行方法**:
```bash
python tests/test_manual_validation.py
```

**出力例**:
```
============================================================
日付バリデーション テスト
本日: 2025-12-13
============================================================

=== 正常ケース ===
✓ 本日: 2025-12-13
  → 2025-12-13
✓ 1週間先: 2025-12-20
  → 2025-12-20

=== 異常ケース ===
✗ 2026-11-29（問題のケース）
  → エラー: 天気予報は最大16日先までしか取得できません。
           指定された日付: 2026-11-29 (351日先)、本日: 2025-12-13
```

**用途**:
- 新機能の動作確認
- デバッグ時の簡易テスト
- ユーザーへのデモ

---

## テスト追加のポリシー

### 1. TDD（テスト駆動開発）の原則

プロジェクトのポリシーとして、TDDで開発を進めます。

**手順**:
1. **期待される動作を定義** - まずテストを作成
2. **テストを実行** - 失敗を確認（Red）
3. **テストをコミット** - テストが正しいことを確認
4. **実装を進める** - テストをパスさせる（Green）
5. **リファクタリング** - コードを改善（Refactor）

参考: `/Users/ryku/.claude/CLAUDE.md` の「Test-Driven Development (TDD)」セクション

### 2. テストファイル命名規則

```
test_<機能名>.py        # 通常のテストファイル
test_manual_<機能名>.py # 手動確認用スクリプト
```

### 3. テストクラス構成

```python
class Test<対象クラス名>:
    """<対象クラス>のテスト"""

    def test_<テストケース名>(self):
        """<期待される動作の説明>"""
        # Arrange（準備）
        # Act（実行）
        # Assert（検証）
```

### 4. テストケース命名規則

**推奨パターン**:
- `test_<条件>_should_<期待される結果>`
- 例: `test_past_date_should_raise_error`

**日本語docstring**:
- テストメソッドには日本語でわかりやすい説明を記載
- 例: `"""過去の日付はエラーを発生させるべき"""`

### 5. 境界値テスト

重要な数値には必ず境界値テストを追加:

```python
def test_16_days_ahead_is_valid(self):
    """16日先は有効（境界値）"""
    future = date.today() + timedelta(days=16)
    validate_date_range(future)  # エラーなし

def test_17_days_ahead_is_invalid(self):
    """17日先は無効（境界値を超える）"""
    future = date.today() + timedelta(days=17)
    with pytest.raises(ValueError):
        validate_date_range(future)
```

### 6. エラーメッセージの検証

エラーメッセージも検証対象:

```python
with pytest.raises(ValueError, match="天気予報は最大16日先までしか取得できません"):
    validate_and_check_date(far_future.isoformat())
```

### 7. 実際のシナリオテスト

実際に発生した問題をテストケースとして追加:

```python
class TestRealWorldScenario:
    """実際のシナリオのテスト"""

    def test_scenario_2026_november_29_should_fail(self):
        """
        実際の問題シナリオ:
        2026年11月29日は現在から遥か未来なので拒否されるべき

        背景:
        - ユーザーが「明日11月29日」と指定
        - LLMが2026-11-29と解釈
        - Open-Meteo APIが400エラーを返した
        """
        with pytest.raises(ValueError, match="天気予報は最大16日先までしか取得できません"):
            validate_and_check_date("2026-11-29")
```

---

## TDD（テスト駆動開発）のアプローチ

### 基本サイクル

```
┌─────────────────────────────────────────┐
│ 1. テストを書く（期待される動作を定義） │
└──────────────────┬──────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│ 2. テストを実行して失敗を確認（Red）     │
└──────────────────┬──────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│ 3. テストをコミット                      │
│    （テストが正しいことを確認）          │
└──────────────────┬──────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│ 4. 実装を書く（テストをパスさせる）      │
│    Green                                 │
└──────────────────┬──────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│ 5. リファクタリング                      │
│    （コードを改善）                      │
└──────────────────┬──────────────────────┘
                   ↓
                 完了
```

### 実践例: 日付範囲チェック機能の追加

#### Step 1: テストを書く

```python
# tests/test_date_range_validation.py
def test_17_days_ahead_is_invalid(self):
    """17日先は無効（境界値を超える）"""
    future = date.today() + timedelta(days=17)
    with pytest.raises(ValueError, match="天気予報は最大16日先までしか取得できません"):
        validate_date_range(future)
```

#### Step 2: テストを実行して失敗を確認

```bash
$ python -m pytest tests/test_date_range_validation.py::TestValidateDateRange::test_17_days_ahead_is_invalid -v

FAILED tests/test_date_range_validation.py::TestValidateDateRange::test_17_days_ahead_is_invalid
# エラー: validate_date_range関数が存在しない
```

#### Step 3: テストをコミット

```bash
git add tests/test_date_range_validation.py
git commit -m "Add test: 17日先の日付は無効とする"
```

#### Step 4: 実装を書く

```python
# src/date_utils.py
MAX_FORECAST_DAYS = 16

def validate_date_range(target_date: date) -> None:
    days_ahead = (target_date - date.today()).days
    if days_ahead > MAX_FORECAST_DAYS:
        raise ValueError(
            f"天気予報は最大{MAX_FORECAST_DAYS}日先までしか取得できません。"
        )
```

#### Step 5: テストが通ることを確認

```bash
$ python -m pytest tests/test_date_range_validation.py::TestValidateDateRange::test_17_days_ahead_is_invalid -v

PASSED tests/test_date_range_validation.py::TestValidateDateRange::test_17_days_ahead_is_invalid
```

#### Step 6: 実装をコミット

```bash
git add src/date_utils.py
git commit -m "Implement: 16日先を超える日付をチェック"
```

---

## トラブルシューティング

### インポートエラー

```
ImportError: cannot import name 'validate_and_check_date' from 'date_utils'
```

**原因**: Python パスが正しく設定されていない

**解決方法**:
```bash
# fishing_mcpディレクトリから実行していることを確認
cd server/fishing_mcp
python -m pytest tests/ -v
```

---

### モックが動作しない

```
TypeError: '<' not supported between instances of 'MagicMock' and 'int'
```

**原因**: モックの設定が不完全

**解決方法**: `test_date_range_validation.py`を参考にしてください。
このファイルはモックを使わずに実際の日付で動作するように設計されています。

---

### pytest が見つからない

```
pytest: command not found
```

**解決方法**:
```bash
# 仮想環境をアクティブ化
source .venv/bin/activate  # または適切なパス

# pytestをインストール
pip install pytest pytest-asyncio
```

---

### テストが遅い

**最適化方法**:
```bash
# 並列実行（pytest-xdistが必要）
pip install pytest-xdist
python -m pytest tests/ -v -n auto
```

---

## 推奨ワークフロー

### 新機能を追加する場合

1. **要件を確認**
   - 何を実装するか明確にする
   - 期待される入出力を定義

2. **テストを作成**
   ```bash
   # 新しいテストファイルを作成
   touch tests/test_<機能名>.py
   ```

3. **テストを実行（失敗を確認）**
   ```bash
   python -m pytest tests/test_<機能名>.py -v
   ```

4. **テストをコミット**
   ```bash
   git add tests/test_<機能名>.py
   git commit -m "Add test: <機能の説明>"
   ```

5. **実装を作成**
   ```bash
   # src/配下に実装ファイルを作成
   ```

6. **テストを実行（成功を確認）**
   ```bash
   python -m pytest tests/test_<機能名>.py -v
   ```

7. **実装をコミット**
   ```bash
   git add src/<実装ファイル>
   git commit -m "Implement: <機能の説明>"
   ```

---

### バグ修正の場合

1. **再現テストを作成**
   - バグを再現するテストケースを追加
   - `TestRealWorldScenario`クラスに追加推奨

2. **テストが失敗することを確認**
   ```bash
   python -m pytest tests/test_<テストファイル>.py -v
   ```

3. **テストをコミット**
   ```bash
   git add tests/
   git commit -m "Add test: <バグの説明>"
   ```

4. **バグを修正**

5. **テストが通ることを確認**
   ```bash
   python -m pytest tests/ -v
   ```

6. **修正をコミット**
   ```bash
   git add src/
   git commit -m "Fix: <バグの説明>"
   ```

---

## 参考リンク

- [pytest公式ドキュメント](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- プロジェクトのTDDポリシー: `/Users/ryku/.claude/CLAUDE.md`

---

## 質問・フィードバック

テストに関する質問や改善提案がある場合は、適切なチャネルで共有してください。
