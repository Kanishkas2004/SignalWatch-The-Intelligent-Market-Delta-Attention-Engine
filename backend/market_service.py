import asyncio
import datetime
import math
import random
import logging
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)

# Canonical seed universe of popular liquid tickers across sectors
BASE_UNIVERSE = {
    "NVDA": {
        "name": "NVIDIA Corporation",
        "sector": "Semiconductors",
        "base_price": 128.50,
        "volatility": 0.032,
        "avg_volume": 68_000_000,
        "sma_50": 122.40,
        "sma_200": 105.80,
        "high_52w": 140.76,
        "low_52w": 40.85,
        "beta": 1.75,
    },
    "AAPL": {
        "name": "Apple Inc.",
        "sector": "Consumer Electronics",
        "base_price": 224.20,
        "volatility": 0.014,
        "avg_volume": 48_000_000,
        "sma_50": 218.60,
        "sma_200": 192.30,
        "high_52w": 237.23,
        "low_52w": 164.08,
        "beta": 0.95,
    },
    "MSFT": {
        "name": "Microsoft Corporation",
        "sector": "Software & Cloud",
        "base_price": 418.75,
        "volatility": 0.016,
        "avg_volume": 21_000_000,
        "sma_50": 425.10,
        "sma_200": 408.20,
        "high_52w": 468.35,
        "low_52w": 309.45,
        "beta": 1.10,
    },
    "TSLA": {
        "name": "Tesla, Inc.",
        "sector": "Automotive & Clean Energy",
        "base_price": 214.60,
        "volatility": 0.038,
        "avg_volume": 72_000_000,
        "sma_50": 225.80,
        "sma_200": 198.50,
        "high_52w": 271.00,
        "low_52w": 138.80,
        "beta": 2.10,
    },
    "AMZN": {
        "name": "Amazon.com, Inc.",
        "sector": "E-Commerce & Cloud",
        "base_price": 178.40,
        "volatility": 0.018,
        "avg_volume": 35_000_000,
        "sma_50": 182.10,
        "sma_200": 165.40,
        "high_52w": 201.20,
        "low_52w": 118.35,
        "beta": 1.25,
    },
    "GOOGL": {
        "name": "Alphabet Inc.",
        "sector": "Internet & Search",
        "base_price": 164.80,
        "volatility": 0.019,
        "avg_volume": 24_000_000,
        "sma_50": 169.50,
        "sma_200": 152.80,
        "high_52w": 191.75,
        "low_52w": 120.21,
        "beta": 1.05,
    },
    "META": {
        "name": "Meta Platforms, Inc.",
        "sector": "Social Media & AI",
        "base_price": 512.30,
        "volatility": 0.024,
        "avg_volume": 18_000_000,
        "sma_50": 498.20,
        "sma_200": 435.60,
        "high_52w": 542.80,
        "low_52w": 279.40,
        "beta": 1.30,
    },
    "AMD": {
        "name": "Advanced Micro Devices",
        "sector": "Semiconductors",
        "base_price": 142.10,
        "volatility": 0.034,
        "avg_volume": 46_000_000,
        "sma_50": 149.30,
        "sma_200": 158.40,
        "high_52w": 227.30,
        "low_52w": 94.04,
        "beta": 1.85,
    },
    "SPY": {
        "name": "SPDR S&P 500 ETF Trust",
        "sector": "Broad Market Index",
        "base_price": 548.20,
        "volatility": 0.008,
        "avg_volume": 55_000_000,
        "sma_50": 542.10,
        "sma_200": 515.30,
        "high_52w": 565.16,
        "low_52w": 410.07,
        "beta": 1.00,
    },
    "QQQ": {
        "name": "Invesco QQQ Trust",
        "sector": "Tech Index",
        "base_price": 472.90,
        "volatility": 0.012,
        "avg_volume": 42_000_000,
        "sma_50": 468.20,
        "sma_200": 435.10,
        "high_52w": 503.52,
        "low_52w": 348.40,
        "beta": 1.20,
    },
    "PLTR": {
        "name": "Palantir Technologies Inc.",
        "sector": "Enterprise Software / AI",
        "base_price": 31.45,
        "volatility": 0.042,
        "avg_volume": 55_000_000,
        "sma_50": 28.50,
        "sma_200": 23.20,
        "high_52w": 34.20,
        "low_52w": 14.48,
        "beta": 2.20,
    },
    "COIN": {
        "name": "Coinbase Global, Inc.",
        "sector": "Digital Assets",
        "base_price": 182.50,
        "volatility": 0.055,
        "avg_volume": 12_000_000,
        "sma_50": 210.40,
        "sma_200": 195.80,
        "high_52w": 283.48,
        "low_52w": 69.63,
        "beta": 2.80,
    }
}

# Real-world styled news catalyst templates
SAMPLE_CATALYSTS = [
    {"type": "EARNINGS", "headline": "{symbol} reports Q2 EPS beat of +18%, raises FY guidance on robust AI demand."},
    {"type": "ANALYST", "headline": "Goldman Sachs reiterates Conviction Buy on {symbol}, increases target price by 15%."},
    {"type": "VOLUME", "headline": "Unusual institutional dark-pool block trades detected in {symbol} with 3.2x normal volume."},
    {"type": "REGULATORY", "headline": "Antitrust inquiry launched into {symbol}'s cloud licensing agreements."},
    {"type": "TECHNICAL", "headline": "{symbol} breaches 50-day moving average resistance with strong momentum."},
    {"type": "MACRO", "headline": "Treasury yield pullback fuels mega-cap tech rotation lifting {symbol}."},
    {"type": "PRODUCT", "headline": "{symbol} unveils next-generation enterprise AI architecture with 2x throughput."}
]


class MarketDataService:
    def __init__(self):
        self.tickers: Dict[str, Dict[str, Any]] = {}
        self.subscribers: List[Callable[[Dict[str, Any]], Any]] = []
        self._is_running = False
        self._bg_task: Optional[asyncio.Task] = None
        self._initialize_universe()

    def _initialize_universe(self):
        now = datetime.datetime.utcnow()
        for sym, meta in BASE_UNIVERSE.items():
            base = meta["base_price"]
            # Generate realistic today open and current
            open_price = round(base * (1 + random.uniform(-0.015, 0.015)), 2)
            current_price = round(open_price * (1 + random.uniform(-0.02, 0.025)), 2)
            high_today = max(open_price, current_price, round(open_price * (1 + random.uniform(0.005, 0.03)), 2))
            low_today = min(open_price, current_price, round(open_price * (1 - random.uniform(0.005, 0.03)), 2))
            current_volume = int(meta["avg_volume"] * random.uniform(0.6, 1.8))

            # Generate realistic 30-day daily historical bars
            historical_bars = []
            curr_bar_price = base * 0.90
            for i in range(30, 0, -1):
                day_date = now - datetime.timedelta(days=i)
                change = random.gauss(0.001, meta["volatility"])
                curr_bar_price = round(curr_bar_price * (1 + change), 2)
                h = round(curr_bar_price * (1 + abs(random.gauss(0.005, 0.01))), 2)
                l = round(curr_bar_price * (1 - abs(random.gauss(0.005, 0.01))), 2)
                vol = int(meta["avg_volume"] * random.uniform(0.7, 1.4))
                historical_bars.append({
                    "date": day_date.strftime("%Y-%m-%d"),
                    "open": round(curr_bar_price * (1 - random.uniform(-0.005, 0.005)), 2),
                    "high": h,
                    "low": l,
                    "close": curr_bar_price,
                    "volume": vol,
                })

            # Generate intraday 5-minute sparkline points (last 78 points for 6.5h)
            sparkline = []
            step_price = open_price
            for step in range(30):
                step_price = round(step_price * (1 + random.gauss(0, meta["volatility"] / 4)), 2)
                sparkline.append(step_price)
            sparkline.append(current_price)

            # Assign seed catalyst if high volatility
            catalysts = []
            if abs((current_price - open_price) / open_price) > 0.02 or sym in ["NVDA", "MSFT", "TSLA", "PLTR"]:
                tmpl = random.choice(SAMPLE_CATALYSTS)
                catalysts.append({
                    "type": tmpl["type"],
                    "headline": tmpl["headline"].format(symbol=sym),
                    "timestamp": (now - datetime.timedelta(minutes=random.randint(15, 180))).isoformat()
                })

            self.tickers[sym] = {
                "symbol": sym,
                "name": meta["name"],
                "sector": meta["sector"],
                "price": current_price,
                "open_today": open_price,
                "high_today": high_today,
                "low_today": low_today,
                "previous_close": base,
                "volume": current_volume,
                "avg_volume": meta["avg_volume"],
                "high_52w": meta["high_52w"],
                "low_52w": meta["low_52w"],
                "sma_50": meta["sma_50"],
                "sma_200": meta["sma_200"],
                "beta": meta["beta"],
                "volatility": meta["volatility"],
                "last_updated": now,
                "data_health": "LIVE",
                "latency_ms": random.randint(18, 45),
                "sparkline_1d": sparkline,
                "historical_bars": historical_bars,
                "catalysts": catalysts,
                "tick_direction": "NONE"
            }

    def register_symbol_if_missing(self, symbol: str) -> Dict[str, Any]:
        sym = symbol.upper().strip()
        if sym in self.tickers:
            return self.tickers[sym]

        # Register dynamic ticker
        now = datetime.datetime.utcnow()
        base_price = round(random.uniform(25.0, 350.0), 2)
        open_price = round(base_price * (1 + random.uniform(-0.01, 0.01)), 2)
        current_price = open_price
        avg_vol = random.randint(5_000_000, 30_000_000)

        self.tickers[sym] = {
            "symbol": sym,
            "name": f"{sym} Corp.",
            "sector": "Technology",
            "price": current_price,
            "open_today": open_price,
            "high_today": round(current_price * 1.015, 2),
            "low_today": round(current_price * 0.985, 2),
            "previous_close": base_price,
            "volume": int(avg_vol * random.uniform(0.7, 1.2)),
            "avg_volume": avg_vol,
            "high_52w": round(current_price * 1.35, 2),
            "low_52w": round(current_price * 0.70, 2),
            "sma_50": round(current_price * 0.96, 2),
            "sma_200": round(current_price * 0.90, 2),
            "beta": 1.20,
            "volatility": 0.025,
            "last_updated": now,
            "data_health": "LIVE",
            "latency_ms": random.randint(20, 50),
            "sparkline_1d": [round(current_price * (1 + random.uniform(-0.01, 0.01)), 2) for _ in range(15)] + [current_price],
            "historical_bars": [],
            "catalysts": [],
            "tick_direction": "NONE"
        }
        return self.tickers[sym]

    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        return self.tickers.get(symbol.upper().strip())

    def get_all_tickers(self) -> Dict[str, Dict[str, Any]]:
        return self.tickers

    def get_sector_benchmarks(self) -> Dict[str, float]:
        """Calculates sector average performance for decoupling detection."""
        sector_moves: Dict[str, List[float]] = {}
        for tick in self.tickers.values():
            sec = tick.get("sector", "Other")
            move_pct = ((tick["price"] - tick["previous_close"]) / tick["previous_close"]) * 100
            sector_moves.setdefault(sec, []).append(move_pct)
        return {sec: round(sum(moves) / len(moves), 2) for sec, moves in sector_moves.items()}

    async def update_tick_simulated(self):
        """Simulates micro-market order flow ticks across watched universe."""
        now = datetime.datetime.utcnow()
        # Randomly choose 1-3 active tickers to tick
        active_symbols = random.sample(list(self.tickers.keys()), min(3, len(self.tickers)))
        updated_ticks = []

        for sym in active_symbols:
            t = self.tickers[sym]
            volat = t["volatility"]
            # Geometric Brownian motion micro-step
            shock = random.gauss(0, volat / 25)
            # Occasional jump shock (0.5% probability)
            if random.random() < 0.03:
                shock += random.choice([-1, 1]) * random.uniform(0.005, 0.015)

            new_price = round(max(0.1, t["price"] * (1 + shock)), 2)
            direction = "UP" if new_price > t["price"] else ("DOWN" if new_price < t["price"] else "NONE")
            t["tick_direction"] = direction
            t["price"] = new_price
            t["high_today"] = max(t["high_today"], new_price)
            t["low_today"] = min(t["low_today"], new_price)
            # Volume increment
            t["volume"] += random.randint(1_000, 15_000)
            t["last_updated"] = now
            t["latency_ms"] = random.randint(15, 38)
            t["data_health"] = "LIVE"

            # Update sparkline
            if len(t["sparkline_1d"]) >= 50:
                t["sparkline_1d"].pop(0)
            t["sparkline_1d"].append(new_price)

            updated_ticks.append({
                "symbol": sym,
                "price": new_price,
                "change_today": round(new_price - t["previous_close"], 2),
                "change_today_pct": round(((new_price - t["previous_close"]) / t["previous_close"]) * 100, 2),
                "volume": t["volume"],
                "direction": direction,
                "timestamp": now.isoformat(),
                "data_health": t["data_health"]
            })

        # Notify subscribers
        for sub in self.subscribers:
            try:
                res = sub(updated_ticks)
                if asyncio.iscoroutine(res):
                    asyncio.create_task(res)
            except Exception as e:
                logger.error(f"Error in subscriber callback: {e}")

    def add_subscriber(self, callback: Callable[[List[Dict[str, Any]]], Any]):
        if callback not in self.subscribers:
            self.subscribers.append(callback)

    def remove_subscriber(self, callback: Callable[[List[Dict[str, Any]]], Any]):
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    async def start_feed_loop(self):
        self._is_running = True
        logger.info("Market data feed loop started.")
        while self._is_running:
            try:
                await self.update_tick_simulated()
                await asyncio.sleep(random.uniform(1.2, 2.5))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in market feed loop: {e}")
                await asyncio.sleep(2.0)

    def stop(self):
        self._is_running = False


market_service = MarketDataService()
