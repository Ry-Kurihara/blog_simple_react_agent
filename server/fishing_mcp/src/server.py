import json
import os
import base64
from pathlib import Path
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.requests import Request

from .models import Spot, WeatherEntry, TideEntry, TideEvent, SunTime, FishingPlanSuggestion, TimeRange
from .weather_client import OpenMeteoWeatherClient
from .tide_client import Tide736Client
from .date_utils import validate_and_check_date, validate_and_check_datetime


# FastMCP インスタンス
mcp = FastMCP("fishing_mcp")

# グローバル変数でクライアントとスポットデータを保持
weather_client: Optional[OpenMeteoWeatherClient] = None
tide_client: Optional[Tide736Client] = None
spots_data: dict[str, Spot] = {}


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """HTTP Basic Authentication Middleware"""

    def __init__(self, app, username: str, password: str):
        super().__init__(app)
        self.username = username
        self.password = password

    async def dispatch(self, request: Request, call_next):
        # Get Authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Basic "):
            return Response(
                content="Unauthorized",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="Fishing MCP"'},
            )

        try:
            # Decode base64 credentials
            credentials = base64.b64decode(auth_header[6:]).decode("utf-8")
            username, password = credentials.split(":", 1)

            # Verify credentials
            if username == self.username and password == self.password:
                response = await call_next(request)
                return response
            else:
                return Response(
                    content="Unauthorized",
                    status_code=401,
                    headers={"WWW-Authenticate": 'Basic realm="Fishing MCP"'},
                )
        except Exception:
            return Response(
                content="Unauthorized",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="Fishing MCP"'},
            )


def load_spots():
    """スポット定義を読み込む"""
    global spots_data
    config_path = Path(__file__).parent.parent / "config" / "spots.json"
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for spot_dict in data["spots"]:
            spot = Spot(**spot_dict)
            spots_data[spot.id] = spot


async def initialize_clients():
    """クライアントを初期化"""
    global weather_client, tide_client
    weather_client = OpenMeteoWeatherClient()
    tide_client = Tide736Client()


@mcp.tool()
async def list_spots() -> dict:
    """
    登録済みの釣りスポット一覧を取得

    Returns:
        スポット一覧
    """
    spots_list = [spot.model_dump() for spot in spots_data.values()]
    return {"spots": spots_list}


@mcp.tool()
async def get_spot_info(spot_id: str) -> dict:
    """
    特定の釣りスポットの詳細情報を取得

    Args:
        spot_id: スポットID (例: "korose_bridge", "tenkubashi")

    Returns:
        スポット詳細情報
    """
    if spot_id not in spots_data:
        return {"error": f"Spot not found: {spot_id}"}

    spot = spots_data[spot_id]
    return {"spot": spot.model_dump()}


@mcp.tool()
async def get_weather(spot_id: str, start: str, end: str) -> dict:
    """
    指定スポットの天気情報を取得

    Args:
        spot_id: スポットID
        start: 開始日時 (ISO8601形式、例: "2025-11-30T05:00:00+09:00")
        end: 終了日時 (ISO8601形式、例: "2025-11-30T10:00:00+09:00")

    Returns:
        天気情報のリスト
    """
    if spot_id not in spots_data:
        return {"error": f"Spot not found: {spot_id}"}

    spot = spots_data[spot_id]

    # 日時の検証（16日先までの範囲チェック）
    try:
        start_dt = validate_and_check_datetime(start)
        end_dt = validate_and_check_datetime(end)
    except ValueError as e:
        return {"error": str(e)}

    try:
        entries = await weather_client.get_hourly_weather(
            latitude=spot.latitude,
            longitude=spot.longitude,
            start=start_dt,
            end=end_dt,
        )
        return {
            "spot_id": spot_id,
            "spot_name": spot.name,
            "entries": [entry.model_dump() for entry in entries],
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def get_tide(spot_id: str, target_date: str) -> dict:
    """
    指定スポットの潮汐情報を取得

    Args:
        spot_id: スポットID
        target_date: 対象日 (YYYY-MM-DD形式、例: "2025-11-30")

    Returns:
        潮汐情報（満潮・干潮イベントと潮位データ）
    """
    if spot_id not in spots_data:
        return {"error": f"Spot not found: {spot_id}"}

    spot = spots_data[spot_id]

    # 日付の検証（16日先までの範囲チェック）
    try:
        date_obj = validate_and_check_date(target_date)
    except ValueError as e:
        return {"error": str(e)}

    try:
        events = await tide_client.get_tide_events(
            pc=spot.tide_station.pc,
            hc=spot.tide_station.hc,
            target_date=date_obj,
        )

        return {
            "spot_id": spot_id,
            "spot_name": spot.name,
            "date": target_date,
            "tide_events": [event.model_dump() for event in events],
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def get_sun_times(spot_id: str, target_date: str) -> dict:
    """
    指定スポットの日の出・日の入り情報を取得

    Args:
        spot_id: スポットID
        target_date: 対象日 (YYYY-MM-DD形式、例: "2025-11-30")

    Returns:
        日の出・日の入り情報
    """
    if spot_id not in spots_data:
        return {"error": f"Spot not found: {spot_id}"}

    spot = spots_data[spot_id]

    # 日付の検証（16日先までの範囲チェック）
    try:
        date_obj = validate_and_check_date(target_date)
    except ValueError as e:
        return {"error": str(e)}

    try:
        sun_times = await tide_client.get_sun_times(
            pc=spot.tide_station.pc,
            hc=spot.tide_station.hc,
            target_date=date_obj,
        )

        if sun_times is None:
            return {"error": "Sun times data not available"}

        return {
            "spot_id": spot_id,
            "spot_name": spot.name,
            "sun_times": sun_times.model_dump(),
        }
    except Exception as e:
        return {"error": str(e)}


class PlanFishingSessionArgs(BaseModel):
    """plan_fishing_sessionの引数"""
    spot_id: str = Field(description="スポットID")
    target_date: str = Field(description="対象日 (YYYY-MM-DD形式)")
    time_window_start: str = Field(description="時間範囲の開始 (HH:MM形式、例: 05:00)")
    time_window_end: str = Field(description="時間範囲の終了 (HH:MM形式、例: 10:00)")
    target_fish: Optional[str] = Field(default=None, description="対象魚種 (例: bass, seabass)")


@mcp.tool()
async def plan_fishing_session(args: PlanFishingSessionArgs) -> dict:
    """
    釣りセッションのプランを生成

    Args:
        args: プラン生成のためのパラメータ

    Returns:
        釣りプラン提案
    """
    spot_id = args.spot_id
    target_date_str = args.target_date
    time_start = args.time_window_start
    time_end = args.time_window_end
    target_fish = args.target_fish

    if spot_id not in spots_data:
        return {"error": f"Spot not found: {spot_id}"}

    spot = spots_data[spot_id]

    # 日付の検証（16日先までの範囲チェック）
    try:
        target_date_obj = validate_and_check_date(target_date_str)
    except ValueError as e:
        return {"error": str(e)}

    tz = ZoneInfo("Asia/Tokyo")

    # 時間範囲を作成
    start_hour, start_minute = map(int, time_start.split(":"))
    end_hour, end_minute = map(int, time_end.split(":"))
    start_dt = datetime.combine(target_date_obj, time(start_hour, start_minute), tzinfo=tz)
    end_dt = datetime.combine(target_date_obj, time(end_hour, end_minute), tzinfo=tz)

    try:
        # 天気情報を取得
        weather_entries = await weather_client.get_hourly_weather(
            latitude=spot.latitude,
            longitude=spot.longitude,
            start=start_dt,
            end=end_dt,
        )

        # 潮汐情報を取得
        tide_events = await tide_client.get_tide_events(
            pc=spot.tide_station.pc,
            hc=spot.tide_station.hc,
            target_date=target_date_obj,
        )

        # 日の出・日の入り情報を取得
        sun_times = await tide_client.get_sun_times(
            pc=spot.tide_station.pc,
            hc=spot.tide_station.hc,
            target_date=target_date_obj,
        )

        # プラン生成ロジック
        recommended_ranges = []
        tactics = []
        lures = []
        risks = []

        # 日の出・日の入りベースの推奨時間
        if sun_times:
            sunrise = sun_times.sunrise
            sunset = sun_times.sunset

            # 朝まずめ（日の出前後1時間）
            if start_dt <= sunrise <= end_dt or start_dt <= sunrise + timedelta(hours=1) <= end_dt:
                morning_start = max(start_dt, sunrise - timedelta(minutes=30))
                morning_end = min(end_dt, sunrise + timedelta(hours=1))
                recommended_ranges.append(TimeRange(
                    start=morning_start,
                    end=morning_end,
                    reason="朝まずめ - 活性が高まる時間帯"
                ))
                tactics.append("朝まずめは表層を攻める")

            # 夕まずめ（日の入り前後1時間）
            if start_dt <= sunset <= end_dt or start_dt <= sunset + timedelta(minutes=30) <= end_dt:
                evening_start = max(start_dt, sunset - timedelta(hours=1))
                evening_end = min(end_dt, sunset + timedelta(minutes=30))
                recommended_ranges.append(TimeRange(
                    start=evening_start,
                    end=evening_end,
                    reason="夕まずめ - 日中の最後のチャンス"
                ))
                tactics.append("夕まずめは積極的にトップウォーターも試す")

        # 潮汐ベースの推奨時間（河口や海のスポットの場合）
        if spot.category in ["estuary", "sea"]:
            for event in tide_events:
                if start_dt <= event.time <= end_dt:
                    # 満潮前後の時間帯
                    if event.type == "high":
                        tide_start = max(start_dt, event.time - timedelta(hours=1))
                        tide_end = min(end_dt, event.time + timedelta(hours=1))
                        recommended_ranges.append(TimeRange(
                            start=tide_start,
                            end=tide_end,
                            reason=f"満潮前後 ({event.time.strftime('%H:%M')}) - ベイトフィッシュが集まる"
                        ))
                        tactics.append("満潮時はストラクチャ周りを丁寧に探る")

        # ルアー提案
        if target_fish == "bass" or (target_fish is None and "bass" in spot.target_fish):
            lures.extend(["クランクベイト", "スピナーベイト", "テキサスリグ"])
        if target_fish == "seabass" or (target_fish is None and "seabass" in spot.target_fish):
            lures.extend(["バイブレーション", "シンキングミノー", "ワーム"])

        # 天気ベースのリスク評価
        for entry in weather_entries:
            if entry.wind_speed_mps > 10:
                risks.append(f"{entry.timestamp.strftime('%H:%M')} 強風注意 ({entry.wind_speed_mps:.1f} m/s)")
            if entry.precipitation_mm and entry.precipitation_mm > 5:
                risks.append(f"{entry.timestamp.strftime('%H:%M')} 強い雨 ({entry.precipitation_mm} mm/h)")

        # プラン作成
        if not recommended_ranges:
            # デフォルトの推奨時間を作成
            recommended_ranges.append(TimeRange(
                start=start_dt,
                end=start_dt + timedelta(hours=2),
                reason="指定された時間帯で釣行可能"
            ))

        if not tactics:
            tactics.append(f"{spot.notes or '通常の釣り方で攻める'}")

        tactics_summary = " / ".join(tactics) if tactics else "通常の釣り方で攻める"
        risk_notes = " / ".join(risks) if risks else None

        plan = FishingPlanSuggestion(
            spot_id=spot_id,
            spot_name=spot.name,
            date=target_date_obj,
            recommended_time_ranges=recommended_ranges,
            tactics_summary=tactics_summary,
            lure_suggestions=lures if lures else ["汎用ルアー"],
            risk_notes=risk_notes,
        )

        return {"plan": plan.model_dump()}

    except Exception as e:
        return {"error": str(e)}


def main():
    """サーバーを起動"""
    import sys
    import asyncio

    # スポットデータを読み込む
    load_spots()

    # クライアントを初期化
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(initialize_clients())

    # Transport モードを環境変数から取得（デフォルトはstdio）
    transport_mode = os.environ.get("MCP_TRANSPORT", "stdio")

    if transport_mode == "stdio":
        mcp.run(transport="stdio")
    elif transport_mode == "streamable-http":
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "5555"))

        # Basic認証の有効化チェック
        basic_auth_user = os.environ.get("MCP_BASIC_AUTH_USER")
        basic_auth_pass = os.environ.get("MCP_BASIC_AUTH_PASS")

        if basic_auth_user and basic_auth_pass:
            # Basic認証を有効化してstreamable-http起動
            run_streamable_http_with_auth(host, port, basic_auth_user, basic_auth_pass)
        else:
            # Basic認証なしで起動
            mcp.run(transport="streamable-http", host=host, port=port)
    elif transport_mode == "sse":
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "5555"))
        mcp.run(transport="sse", host=host, port=port)
    else:
        print(f"Unknown transport mode: {transport_mode}", file=sys.stderr)
        sys.exit(1)


def run_streamable_http_with_auth(host: str, port: int, username: str, password: str):
    """streamable-httpをBasic認証付きで起動"""
    import asyncio
    import uvicorn
    from starlette.applications import Starlette

    # FastMCPのstreamable-httpアプリケーションを取得
    starlette_app = mcp.streamable_http_app()

    # Basic認証ミドルウェアを追加
    starlette_app.add_middleware(BasicAuthMiddleware, username=username, password=password)

    # uvicornで起動
    config = uvicorn.Config(
        starlette_app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)

    # 非同期実行
    asyncio.run(server.serve())


if __name__ == "__main__":
    main()
