from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime


class UserBase(BaseModel):
    username: str
    display_name: str
    persona: str = "Momentum Trader"


class UserOut(UserBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class WatchlistItemCreate(BaseModel):
    symbol: str
    custom_notes: Optional[str] = ""
    tags: Optional[List[str]] = []
    target_price: Optional[float] = None
    custom_sensitivity: Optional[str] = "normal"  # high, normal, low


class WatchlistItemOut(BaseModel):
    id: int
    watchlist_id: int
    symbol: str
    custom_notes: str
    tags: List[str]
    target_price: Optional[float]
    custom_sensitivity: str
    added_at: datetime
    model_config = ConfigDict(from_attributes=True)


class WatchlistCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    symbols: Optional[List[str]] = []


class WatchlistOut(BaseModel):
    id: int
    user_id: int
    name: str
    description: str
    is_default: bool
    created_at: datetime
    items: List[WatchlistItemOut] = []
    model_config = ConfigDict(from_attributes=True)


class SnapshotOut(BaseModel):
    id: int
    user_id: int
    visit_time: datetime
    label: str
    prices: Dict[str, float]
    model_config = ConfigDict(from_attributes=True)


class AttentionDetail(BaseModel):
    composite_score: float  # 0 to 100
    tier: str  # PRIORITY, NOTEWORTHY, STEADY
    reasons: List[str]  # Human-readable catalyst & anomaly explanations
    delta_since_visit_pct: float
    price_at_visit: Optional[float]
    z_score: float
    rvol: float
    crossed_sma50: bool
    crossed_sma200: bool
    crossed_52w_high: bool
    crossed_52w_low: bool
    sector_divergence_pct: float
    catalysts: List[str]


class TickerAnalysis(BaseModel):
    symbol: str
    company_name: str
    sector: str
    price: float
    change_today: float
    change_today_pct: float
    high_today: float
    low_today: float
    volume: int
    avg_volume: int
    high_52w: float
    low_52w: float
    sma_50: float
    sma_200: float
    attention: AttentionDetail
    data_health: str  # LIVE, DELAYED, STALE, SIMULATED
    latency_ms: int
    last_updated: datetime
    sparkline_1d: List[float] = []
    historical_bars: List[Dict[str, Any]] = []


class ExecutiveDigest(BaseModel):
    last_visit_time: datetime
    elapsed_text: str
    total_watched: int
    priority_count: int
    noteworthy_count: int
    steady_count: int
    headline_summary: str
    action_bullets: List[str]
    sector_pulse: Dict[str, float]


class MarketAlertOut(BaseModel):
    id: int
    symbol: str
    alert_type: str
    severity: str
    headline: str
    details: str
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


class SimulateVisitRequest(BaseModel):
    simulated_minutes_ago: int
