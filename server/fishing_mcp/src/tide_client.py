import httpx
from datetime import datetime, date, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

try:
    from .models import TideEntry, TideEvent, SunTime
except ImportError:
    # スタンドアロン実行時
    from models import TideEntry, TideEvent, SunTime


class Tide736Client:
    """Tide736.net潮汐APIクライアント"""

    BASE_URL = "https://tide736.net/api/get_tide.php"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def get_tide_data(
        self,
        pc: str,
        hc: str,
        target_date: date,
        range_type: str = "day"
    ) -> dict:
        """
        潮汐データを取得

        Args:
            pc: 都道府県コード
            hc: 港コード
            target_date: 対象日
            range_type: 範囲タイプ ("day", "week", "month")

        Returns:
            潮汐データ
        """
        params = {
            "pc": pc,
            "hc": hc,
            "yr": target_date.year,
            "mn": target_date.month,
            "dy": target_date.day,
            "rg": range_type,
        }

        response = await self.client.get(self.BASE_URL, params=params)
        response.raise_for_status()
        return response.json()

    async def get_tide_entries(
        self,
        pc: str,
        hc: str,
        target_date: date,
    ) -> list[TideEntry]:
        """
        指定日の潮汐情報を取得

        Args:
            pc: 都道府県コード
            hc: 港コード
            target_date: 対象日

        Returns:
            潮汐情報のリスト
        """
        data = await self.get_tide_data(pc, hc, target_date, "day")

        entries = []
        tide_data = data.get("tide", {})
        chart_data = tide_data.get("chart", {})

        # 日付をキーとしてデータを取得
        date_key = target_date.isoformat()
        day_data = chart_data.get(date_key, {})

        # tide配列から時系列データを取得
        tide_points = day_data.get("tide", [])

        if not tide_points:
            return entries

        tz = ZoneInfo("Asia/Tokyo")

        for point in tide_points:
            time_str = point.get("time", "")
            level_cm = point.get("cm")

            if not time_str or level_cm is None:
                continue

            # "HH:MM" 形式をパース
            try:
                hour, minute = map(int, time_str.split(":"))
                timestamp = datetime.combine(target_date, time(hour, minute), tzinfo=tz)
            except:
                continue

            entry = TideEntry(
                timestamp=timestamp,
                tide_level_cm=float(level_cm),
                tide_phase="unknown",  # APIからは直接提供されない
            )
            entries.append(entry)

        return entries

    async def get_tide_events(
        self,
        pc: str,
        hc: str,
        target_date: date,
    ) -> list[TideEvent]:
        """
        満潮・干潮のイベントを取得

        Args:
            pc: 都道府県コード
            hc: 港コード
            target_date: 対象日

        Returns:
            満潮・干潮イベントのリスト
        """
        data = await self.get_tide_data(pc, hc, target_date, "day")

        events = []
        tide_data = data.get("tide", {})
        chart_data = tide_data.get("chart", {})

        # 日付をキーとしてデータを取得
        date_key = target_date.isoformat()
        day_data = chart_data.get(date_key, {})

        # edd配列から満潮・干潮イベントを取得
        edd_events = day_data.get("edd", [])

        tz = ZoneInfo("Asia/Tokyo")

        for event_data in edd_events:
            time_str = event_data.get("time", "")
            level_cm = event_data.get("cm")

            if not time_str or level_cm is None:
                continue

            try:
                # "HH:MM" 形式をパース
                hour, minute = map(int, time_str.split(":"))
                timestamp = datetime.combine(target_date, time(hour, minute), tzinfo=tz)

                # eddは満潮・干潮イベント（干満の極値）
                # 潮位が高い方を満潮、低い方を干潮と判定
                # 実際のAPIでは明示的な区別がないので、レベルで判断
                event_type = "high" if float(level_cm) > 100 else "low"

                events.append(TideEvent(
                    time=timestamp,
                    type=event_type,
                    level_cm=float(level_cm)
                ))
            except:
                continue

        # 時刻順にソート
        events.sort(key=lambda e: e.time)
        return events

    async def get_sun_times(
        self,
        pc: str,
        hc: str,
        target_date: date,
    ) -> Optional[SunTime]:
        """
        日の出・日の入り情報を取得

        Args:
            pc: 都道府県コード
            hc: 港コード
            target_date: 対象日

        Returns:
            日の出・日の入り情報
        """
        data = await self.get_tide_data(pc, hc, target_date, "day")

        tide_data = data.get("tide", {})
        chart_data = tide_data.get("chart", {})

        # 日付をキーとしてデータを取得
        date_key = target_date.isoformat()
        day_data = chart_data.get(date_key, {})

        sun_data = day_data.get("sun", {})
        if not sun_data:
            return None

        tz = ZoneInfo("Asia/Tokyo")

        # 日の出
        sunrise_str = sun_data.get("rise", "")
        if sunrise_str:
            try:
                hour, minute = map(int, sunrise_str.split(":"))
                sunrise = datetime.combine(target_date, time(hour, minute), tzinfo=tz)
            except:
                sunrise = None
        else:
            sunrise = None

        # 日の入り
        sunset_str = sun_data.get("set", "")
        if sunset_str:
            try:
                hour, minute = map(int, sunset_str.split(":"))
                sunset = datetime.combine(target_date, time(hour, minute), tzinfo=tz)
            except:
                sunset = None
        else:
            sunset = None

        if sunrise and sunset:
            return SunTime(
                date=target_date,
                sunrise=sunrise,
                sunset=sunset,
            )

        return None


async def main():
    """テスト用メイン関数"""
    import json

    print("=== Tide736 API テスト ===\n")

    # 東京港（pc=13, hc=14）
    pc = "13"
    hc = "14"
    target_date = date.today()

    print(f"港: 東京港（都道府県コード: {pc}, 港コード: {hc}）")
    print(f"対象日: {target_date.isoformat()}\n")

    client = Tide736Client()
    try:
        # 生データの取得
        print("--- 生データ取得 ---")
        raw_data = await client.get_tide_data(pc, hc, target_date, "day")
        print(f"レスポンス構造: {list(raw_data.keys())}")
        print(f"JSON（一部）:\n{json.dumps(raw_data, indent=2, ensure_ascii=False, default=str)[:1000]}...\n")

        # tide構造の詳細を確認
        tide_data = raw_data.get("tide", {})
        print(f"tide構造: {list(tide_data.keys())}\n")

        # 満潮・干潮イベントの取得
        print("--- 満潮・干潮イベント ---")
        events = await client.get_tide_events(pc, hc, target_date)
        print(f"イベント数: {len(events)}件\n")

        for i, event in enumerate(events):
            event_type = "満潮" if event.type == "high" else "干潮"
            print(f"[{i+1}] {event.time.strftime('%H:%M')} {event_type} - 潮位: {event.level_cm:.0f} cm")

        # 日の出・日の入り情報の取得
        print("\n--- 日の出・日の入り ---")
        sun_times = await client.get_sun_times(pc, hc, target_date)
        if sun_times:
            print(f"日の出: {sun_times.sunrise.strftime('%H:%M')}")
            print(f"日の入り: {sun_times.sunset.strftime('%H:%M')}")
        else:
            print("日の出・日の入り情報が取得できませんでした")

        # 潮汐エントリの取得（最初の10件のみ表示）
        print("\n--- 潮汐データ（最初の10件） ---")
        tide_entries = await client.get_tide_entries(pc, hc, target_date)
        print(f"データ点数: {len(tide_entries)}件\n")

        for i, entry in enumerate(tide_entries[:10]):
            phase_jp = {
                "high": "満潮",
                "low": "干潮",
                "rising": "上げ潮",
                "falling": "下げ潮",
                "unknown": "不明"
            }.get(entry.tide_phase, entry.tide_phase)

            level_str = f"{entry.tide_level_cm:.0f} cm" if entry.tide_level_cm else "N/A"
            print(f"{entry.timestamp.strftime('%H:%M')}: {level_str} ({phase_jp})")

    except httpx.HTTPStatusError as e:
        print(f"HTTPエラーが発生しました: {e}")
        print(f"ステータスコード: {e.response.status_code}")
        print(f"レスポンス: {e.response.text[:200]}")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
