import pytest
import datetime
from backend.intelligence_engine import intelligence_engine
from backend.models import AttentionDetail


def test_delta_since_visit_calculation():
    ticker_data = {
        "symbol": "NVDA",
        "name": "NVIDIA Corporation",
        "sector": "Semiconductors",
        "price": 130.00,
        "previous_close": 125.00,
        "open_today": 126.00,
        "volatility": 0.03,
        "volume": 70_000_000,
        "avg_volume": 60_000_000,
        "sma_50": 120.00,
        "sma_200": 100.00,
        "high_52w": 140.00,
        "low_52w": 50.00,
        "catalysts": [],
    }
    sector_benchmarks = {"Semiconductors": 0.5}

    # Test 1: Price moved significantly up since visit ($120 -> $130 = +8.33%)
    attention = intelligence_engine.compute_ticker_attention(
        ticker_data=ticker_data,
        price_at_visit=120.00,
        sector_benchmarks=sector_benchmarks,
        custom_sensitivity="normal",
    )

    assert attention.delta_since_visit_pct == 8.33
    assert attention.price_at_visit == 120.00
    assert attention.composite_score >= 30.0
    assert any("surged" in r.lower() or "moved" in r.lower() for r in attention.reasons)


def test_volatility_z_score_anomaly():
    ticker_data = {
        "symbol": "KO",
        "name": "Coca-Cola Co.",
        "sector": "Consumer Staples",
        "price": 66.00,
        "previous_close": 60.00,
        "open_today": 60.00,
        "volatility": 0.01,  # Low historical volatility
        "volume": 20_000_000,
        "avg_volume": 15_000_000,
        "sma_50": 61.00,
        "sma_200": 58.00,
        "high_52w": 70.00,
        "low_52w": 50.00,
        "catalysts": [],
    }
    sector_benchmarks = {"Consumer Staples": 0.0}

    # 10% move on a 1% volatility stock is a 10-sigma outlier
    attention = intelligence_engine.compute_ticker_attention(
        ticker_data=ticker_data,
        price_at_visit=60.00,
        sector_benchmarks=sector_benchmarks,
        custom_sensitivity="normal",
    )

    assert attention.z_score >= 3.0
    assert attention.tier == "PRIORITY"
    assert any("volatility" in r.lower() for r in attention.reasons)


def test_volume_anomaly_rvol():
    ticker_data = {
        "symbol": "TSLA",
        "name": "Tesla, Inc.",
        "sector": "Automotive",
        "price": 210.00,
        "previous_close": 210.00,
        "open_today": 210.00,
        "volatility": 0.035,
        "volume": 180_000_000,  # 3x expected volume
        "avg_volume": 60_000_000,
        "sma_50": 210.00,
        "sma_200": 200.00,
        "high_52w": 280.00,
        "low_52w": 140.00,
        "catalysts": [],
    }
    sector_benchmarks = {"Automotive": 0.0}

    attention = intelligence_engine.compute_ticker_attention(
        ticker_data=ticker_data,
        price_at_visit=210.00,
        sector_benchmarks=sector_benchmarks,
        custom_sensitivity="normal",
    )

    assert attention.rvol >= 2.5
    assert any("volume" in r.lower() for r in attention.reasons)


def test_executive_digest_generation():
    sector_benchmarks = {"Tech": 1.2, "Auto": -0.8}
    now = datetime.datetime.utcnow()
    last_visit = now - datetime.timedelta(hours=3, minutes=15)

    ticker_analysis_sample = [
        intelligence_engine.analyze_ticker(
            ticker_data={
                "symbol": "NVDA",
                "name": "NVIDIA",
                "sector": "Tech",
                "price": 132.0,
                "previous_close": 126.0,
                "open_today": 127.0,
                "volatility": 0.03,
                "volume": 80_000_000,
                "avg_volume": 60_000_000,
                "high_today": 133.0,
                "low_today": 126.5,
                "sma_50": 122.0,
                "sma_200": 105.0,
                "high_52w": 140.0,
                "low_52w": 40.0,
                "catalysts": [{"headline": "Record Datacenter Orders Announced"}],
            },
            price_at_visit=126.0,
            sector_benchmarks=sector_benchmarks,
        ),
        intelligence_engine.analyze_ticker(
            ticker_data={
                "symbol": "AAPL",
                "name": "Apple",
                "sector": "Tech",
                "price": 224.0,
                "previous_close": 223.8,
                "open_today": 223.9,
                "volatility": 0.015,
                "volume": 40_000_000,
                "avg_volume": 50_000_000,
                "high_today": 224.5,
                "low_today": 223.5,
                "sma_50": 218.0,
                "sma_200": 195.0,
                "high_52w": 235.0,
                "low_52w": 165.0,
                "catalysts": [],
            },
            price_at_visit=223.8,
            sector_benchmarks=sector_benchmarks,
        )
    ]

    digest = intelligence_engine.generate_executive_digest(
        analyzed_tickers=ticker_analysis_sample,
        last_visit_time=last_visit,
        sector_benchmarks=sector_benchmarks,
    )

    assert "3h 15m ago" in digest.elapsed_text
    assert digest.total_watched == 2
    assert len(digest.action_bullets) >= 1
    assert "NVDA" in digest.action_bullets[0]
