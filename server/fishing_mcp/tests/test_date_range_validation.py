"""
日付範囲検証のテスト

16日先までの範囲チェック機能のテスト

テスト実行:
    pytest server/fishing_mcp/tests/test_date_range_validation.py -v
"""

import pytest
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from date_utils import validate_and_check_date, validate_and_check_datetime, validate_date_range


class TestValidateDateRange:
    """validate_date_range 関数のテスト"""

    def test_today_is_valid(self):
        """本日の日付は有効"""
        today = date.today()
        # エラーが発生しないことを確認
        validate_date_range(today)

    def test_tomorrow_is_valid(self):
        """明日の日付は有効"""
        tomorrow = date.today() + timedelta(days=1)
        validate_date_range(tomorrow)

    def test_16_days_ahead_is_valid(self):
        """16日先は有効（境界値）"""
        future = date.today() + timedelta(days=16)
        validate_date_range(future)

    def test_17_days_ahead_is_invalid(self):
        """17日先は無効（境界値を超える）"""
        future = date.today() + timedelta(days=17)
        with pytest.raises(ValueError, match="天気予報は最大16日先までしか取得できません"):
            validate_date_range(future)

    def test_far_future_is_invalid(self):
        """遥か未来の日付は無効"""
        far_future = date.today() + timedelta(days=365)
        with pytest.raises(ValueError, match="天気予報は最大16日先までしか取得できません"):
            validate_date_range(far_future)

    def test_yesterday_is_invalid(self):
        """昨日の日付は無効"""
        yesterday = date.today() - timedelta(days=1)
        with pytest.raises(ValueError, match="過去の日付は指定できません"):
            validate_date_range(yesterday)

    def test_past_date_is_invalid(self):
        """過去の日付は無効"""
        past = date.today() - timedelta(days=30)
        with pytest.raises(ValueError, match="過去の日付は指定できません"):
            validate_date_range(past)


class TestValidateAndCheckDate:
    """validate_and_check_date 関数のテスト"""

    def test_valid_date_string(self):
        """有効な日付文字列"""
        tomorrow = date.today() + timedelta(days=1)
        result = validate_and_check_date(tomorrow.isoformat())
        assert result == tomorrow

    def test_invalid_format(self):
        """無効な日付フォーマット"""
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_and_check_date("2025/12/13")  # スラッシュ区切り

    def test_future_date_beyond_limit(self):
        """16日先を超える日付"""
        far_future = date.today() + timedelta(days=20)
        with pytest.raises(ValueError, match="天気予報は最大16日先までしか取得できません"):
            validate_and_check_date(far_future.isoformat())

    def test_past_date(self):
        """過去の日付"""
        past = date.today() - timedelta(days=1)
        with pytest.raises(ValueError, match="過去の日付は指定できません"):
            validate_and_check_date(past.isoformat())


class TestValidateAndCheckDatetime:
    """validate_and_check_datetime 関数のテスト"""

    def test_valid_datetime_string(self):
        """有効な日時文字列"""
        tomorrow = datetime.now(ZoneInfo("Asia/Tokyo")) + timedelta(days=1)
        result = validate_and_check_datetime(tomorrow.isoformat())
        assert result.date() == tomorrow.date()

    def test_invalid_format(self):
        """無効な日時フォーマット（スペース区切りは実際には有効なので別のテスト）"""
        with pytest.raises(ValueError, match="Invalid datetime format"):
            validate_and_check_datetime("not-a-datetime")

    def test_future_datetime_beyond_limit(self):
        """16日先を超える日時"""
        far_future = datetime.now(ZoneInfo("Asia/Tokyo")) + timedelta(days=20)
        with pytest.raises(ValueError, match="天気予報は最大16日先までしか取得できません"):
            validate_and_check_datetime(far_future.isoformat())


class TestRealWorldScenario:
    """実際のシナリオのテスト"""

    def test_scenario_2026_november_29_should_fail(self):
        """
        実際の問題シナリオ:
        2026年11月29日は現在から遥か未来なので拒否されるべき
        """
        # 2026-11-29は約1年先なので確実に16日を超える
        with pytest.raises(ValueError, match="天気予報は最大16日先までしか取得できません"):
            validate_and_check_date("2026-11-29")

    def test_scenario_valid_week_ahead(self):
        """
        実際のシナリオ:
        1週間先の日付は有効
        """
        week_ahead = date.today() + timedelta(days=7)
        result = validate_and_check_date(week_ahead.isoformat())
        assert result == week_ahead

    def test_scenario_2_weeks_ahead(self):
        """
        実際のシナリオ:
        2週間先の日付は有効（14日先）
        """
        two_weeks = date.today() + timedelta(days=14)
        result = validate_and_check_date(two_weeks.isoformat())
        assert result == two_weeks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
