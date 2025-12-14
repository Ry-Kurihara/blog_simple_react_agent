"""
手動テスト用スクリプト

date_utils.pyのvalidate関数の動作を確認するための簡易テスト

実行方法:
    python server/fishing_mcp/tests/test_manual_validation.py
"""

import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from date_utils import validate_and_check_date, validate_and_check_datetime


def test_valid_cases():
    """正常ケースのテスト"""
    print("=== 正常ケース ===")

    # 本日
    today = date.today()
    print(f"✓ 本日: {today}")
    result = validate_and_check_date(today.isoformat())
    print(f"  → {result}")

    # 1週間先
    week_ahead = today + timedelta(days=7)
    print(f"✓ 1週間先: {week_ahead}")
    result = validate_and_check_date(week_ahead.isoformat())
    print(f"  → {result}")

    # 16日先（境界値）
    max_date = today + timedelta(days=16)
    print(f"✓ 16日先（境界値）: {max_date}")
    result = validate_and_check_date(max_date.isoformat())
    print(f"  → {result}")

    print()


def test_invalid_cases():
    """異常ケースのテスト"""
    print("=== 異常ケース ===")

    # 過去の日付
    yesterday = date.today() - timedelta(days=1)
    print(f"✗ 昨日: {yesterday}")
    try:
        validate_and_check_date(yesterday.isoformat())
        print("  → エラーが発生しませんでした（問題）")
    except ValueError as e:
        print(f"  → エラー: {e}")

    # 17日先
    too_far = date.today() + timedelta(days=17)
    print(f"✗ 17日先: {too_far}")
    try:
        validate_and_check_date(too_far.isoformat())
        print("  → エラーが発生しませんでした（問題）")
    except ValueError as e:
        print(f"  → エラー: {e}")

    # 問題のあった2026-11-29
    print(f"✗ 2026-11-29（問題のケース）")
    try:
        validate_and_check_date("2026-11-29")
        print("  → エラーが発生しませんでした（問題）")
    except ValueError as e:
        print(f"  → エラー: {e}")

    print()


def test_datetime_cases():
    """日時のテスト"""
    print("=== 日時のテスト ===")

    # 正常ケース
    tomorrow_noon = (date.today() + timedelta(days=1)).isoformat() + "T12:00:00+09:00"
    print(f"✓ 明日の正午: {tomorrow_noon}")
    result = validate_and_check_datetime(tomorrow_noon)
    print(f"  → {result}")

    # 異常ケース
    far_future = "2026-11-29T05:00:00+09:00"
    print(f"✗ 2026年11月29日朝5時: {far_future}")
    try:
        validate_and_check_datetime(far_future)
        print("  → エラーが発生しませんでした（問題）")
    except ValueError as e:
        print(f"  → エラー: {e}")

    print()


if __name__ == "__main__":
    print("=" * 60)
    print("日付バリデーション テスト")
    print(f"本日: {date.today()}")
    print("=" * 60)
    print()

    test_valid_cases()
    test_invalid_cases()
    test_datetime_cases()

    print("=" * 60)
    print("テスト完了")
    print("=" * 60)
