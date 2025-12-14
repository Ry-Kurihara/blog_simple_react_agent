"""
日付・日時のバリデーションユーティリティ

Open-Meteo APIの制限（16日先まで）を考慮した日付検証を行います。
"""

import logging
from datetime import date, datetime, timedelta


logger = logging.getLogger(__name__)

# Open-Meteo APIの予報可能な最大日数
MAX_FORECAST_DAYS = 16


def validate_date_range(target_date: date) -> None:
    """
    日付がOpen-Meteo APIの予報可能範囲内かチェックする

    Args:
        target_date: チェック対象の日付

    Raises:
        ValueError: 日付が予報可能範囲外の場合
    """
    today = date.today()
    days_ahead = (target_date - today).days

    # 過去の日付
    if days_ahead < 0:
        raise ValueError(
            f"過去の日付は指定できません。指定された日付: {target_date}、本日: {today}"
        )

    # 16日先を超える未来の日付
    if days_ahead > MAX_FORECAST_DAYS:
        raise ValueError(
            f"天気予報は最大{MAX_FORECAST_DAYS}日先までしか取得できません。"
            f"指定された日付: {target_date} ({days_ahead}日先)、本日: {today}"
        )


def validate_and_check_date(date_str: str) -> date:
    """
    日付文字列を検証し、予報可能範囲内かチェックする

    Args:
        date_str: 日付文字列 (YYYY-MM-DD形式)

    Returns:
        検証済みの日付オブジェクト

    Raises:
        ValueError: 日付フォーマットが不正、または予報可能範囲外の場合
    """
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError as e:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD") from e

    validate_date_range(target_date)
    return target_date


def validate_and_check_datetime(dt_str: str) -> datetime:
    """
    日時文字列を検証し、予報可能範囲内かチェックする

    Args:
        dt_str: 日時文字列 (ISO8601形式)

    Returns:
        検証済みのdatetimeオブジェクト

    Raises:
        ValueError: 日時フォーマットが不正、または予報可能範囲外の場合
    """
    try:
        target_dt = datetime.fromisoformat(dt_str)
    except ValueError as e:
        raise ValueError(f"Invalid datetime format: {dt_str}. Expected ISO8601") from e

    validate_date_range(target_dt.date())
    return target_dt
