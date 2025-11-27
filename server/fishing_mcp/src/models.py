from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class TideStation(BaseModel):
    """潮汐観測所情報"""
    pc: str  # 都道府県コード
    hc: str  # 港コード
    name: str  # 観測所名


class Spot(BaseModel):
    """釣り場情報"""
    id: str
    name: str
    category: str  # "river", "estuary", "sea", "lake"
    latitude: float
    longitude: float
    description: Optional[str] = None
    target_fish: list[str]
    notes: Optional[str] = None
    tide_station: TideStation


class WeatherEntry(BaseModel):
    """天気情報（1時間単位）"""
    timestamp: datetime
    temperature_c: float
    wind_speed_mps: float
    wind_direction_deg: Optional[float] = None
    precipitation_mm: Optional[float] = None
    cloud_cover_percent: Optional[float] = None


class TideEntry(BaseModel):
    """潮汐情報"""
    timestamp: datetime
    tide_level_cm: Optional[float] = None
    tide_phase: str  # "high", "low", "rising", "falling"


class TideEvent(BaseModel):
    """満潮・干潮イベント"""
    time: datetime
    type: str  # "high" or "low"
    level_cm: float


class SunTime(BaseModel):
    """太陽情報"""
    date: date
    sunrise: datetime
    sunset: datetime
    civil_dawn: Optional[datetime] = None
    civil_dusk: Optional[datetime] = None


class TimeRange(BaseModel):
    """時間範囲"""
    start: datetime
    end: datetime
    reason: str


class FishingPlanSuggestion(BaseModel):
    """釣りプラン提案"""
    spot_id: str
    spot_name: str
    date: date
    recommended_time_ranges: list[TimeRange]
    tactics_summary: str
    lure_suggestions: list[str]
    risk_notes: Optional[str] = None
