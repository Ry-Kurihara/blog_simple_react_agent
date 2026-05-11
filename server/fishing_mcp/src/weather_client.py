import httpx
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

try:
    from .models import WeatherEntry
except ImportError:
    # スタンドアロン実行時
    from models import WeatherEntry


class OpenMeteoWeatherClient:
    """Open-Meteo天気APIクライアント"""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def get_hourly_weather(
        self,
        latitude: float,
        longitude: float,
        start: datetime,
        end: datetime,
        timezone: str = "Asia/Tokyo"
    ) -> list[WeatherEntry]:
        """
        指定地点の時間ごとの天気を取得

        Args:
            latitude: 緯度
            longitude: 経度
            start: 開始日時
            end: 終了日時
            timezone: タイムゾーン

        Returns:
            天気情報のリスト
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,precipitation,wind_speed_10m,wind_direction_10m,cloud_cover",
            "start_date": start.date().isoformat(),
            "end_date": end.date().isoformat(),
            "timezone": timezone,
        }

        response = await self.client.get(self.BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        entries = []
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        precips = hourly.get("precipitation", [])
        wind_speeds = hourly.get("wind_speed_10m", [])
        wind_dirs = hourly.get("wind_direction_10m", [])
        cloud_covers = hourly.get("cloud_cover", [])

        for i, time_str in enumerate(times):
            # タイムゾーン情報を含むdatetimeに変換
            timestamp = datetime.fromisoformat(time_str)
            # タイムゾーンがない場合は、指定されたタイムゾーンを設定
            if timestamp.tzinfo is None:
                tz = ZoneInfo(timezone)
                timestamp = timestamp.replace(tzinfo=tz)
            # 指定された時間範囲内のみ
            if start <= timestamp <= end:
                entry = WeatherEntry(
                    timestamp=timestamp,
                    temperature_c=temps[i] if i < len(temps) else 0.0,
                    wind_speed_mps=wind_speeds[i] / 3.6 if i < len(wind_speeds) else 0.0,  # km/h -> m/s
                    wind_direction_deg=wind_dirs[i] if i < len(wind_dirs) else None,
                    precipitation_mm=precips[i] if i < len(precips) else None,
                    cloud_cover_percent=cloud_covers[i] if i < len(cloud_covers) else None,
                )
                entries.append(entry)

        return entries


async def main():
    """テスト用メイン関数"""
    import json

    print("=== Open-Meteo Weather API テスト ===\n")

    # 是政橋の座標
    latitude = 35.6507
    longitude = 139.5327

    # 現在時刻から24時間分の天気を取得
    tz = ZoneInfo("Asia/Tokyo")
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    print(f"地点: 是政橋付近")
    print(f"緯度: {latitude}, 経度: {longitude}")
    print(f"取得期間: {start.isoformat()} ～ {end.isoformat()}\n")

    client = OpenMeteoWeatherClient()
    try:
        entries = await client.get_hourly_weather(
            latitude=latitude,
            longitude=longitude,
            start=start,
            end=end,
        )

        print(f"取得データ数: {len(entries)}件\n")

        # 最初の5件を表示
        print("--- 最初の5件 ---")
        for i, entry in enumerate(entries[:5]):
            print(f"\n[{i+1}] {entry.timestamp.strftime('%Y-%m-%d %H:%M')}")
            print(f"  気温: {entry.temperature_c:.1f}°C")
            print(f"  風速: {entry.wind_speed_mps:.1f} m/s")
            if entry.wind_direction_deg is not None:
                print(f"  風向: {entry.wind_direction_deg:.0f}°")
            if entry.precipitation_mm is not None and entry.precipitation_mm > 0:
                print(f"  降水量: {entry.precipitation_mm:.1f} mm/h")
            if entry.cloud_cover_percent is not None:
                print(f"  雲量: {entry.cloud_cover_percent:.0f}%")

        # 全データをJSONで保存（オプション）
        print("\n--- JSONデータ（最初の3件） ---")
        json_data = [entry.model_dump(mode='json') for entry in entries[:3]]
        print(json.dumps(json_data, indent=2, ensure_ascii=False, default=str))

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
