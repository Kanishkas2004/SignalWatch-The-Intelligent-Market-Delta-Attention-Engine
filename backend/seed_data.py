import datetime
import json
from backend.database import SessionLocal, init_db, User, Watchlist, WatchlistItem, UserVisitSnapshot, MarketAlert
from backend.market_service import market_service, BASE_UNIVERSE


def seed_database():
    init_db()
    db = SessionLocal()

    try:
        # Check if already seeded
        if db.query(User).first():
            print("Database already seeded.")
            return

        print("Seeding initial users and watchlists...")
        now = datetime.datetime.utcnow()

        # User 1: Momentum Tech Trader (Default)
        user_alex = User(
            username="alex_trader",
            display_name="Alex Reed",
            persona="Tech Momentum Trader",
            created_at=now - datetime.timedelta(days=45),
        )
        # User 2: Macro & Value Strategist
        user_elena = User(
            username="elena_macro",
            display_name="Elena Rostova",
            persona="Macro & Value Strategist",
            created_at=now - datetime.timedelta(days=30),
        )
        # User 3: AI Specialist
        user_sam = User(
            username="sam_analyst",
            display_name="Sam Vance",
            persona="Semiconductor & AI Specialist",
            created_at=now - datetime.timedelta(days=15),
        )

        db.add_all([user_alex, user_elena, user_sam])
        db.commit()

        # Watchlists for Alex
        wl_tech = Watchlist(
            user_id=user_alex.id,
            name="Mega-Cap Titans",
            description="Core hyperscalers and mega-cap tech bellwethers",
            is_default=True,
            created_at=now - datetime.timedelta(days=20),
        )
        wl_growth = Watchlist(
            user_id=user_alex.id,
            name="High-Beta Growth & AI",
            description="High volatility momentum and AI infrastructure plays",
            is_default=False,
            created_at=now - datetime.timedelta(days=12),
        )
        wl_macro = Watchlist(
            user_id=user_alex.id,
            name="Macro & Benchmarks",
            description="Broad market index ETFs and defensive liquid anchors",
            is_default=False,
            created_at=now - datetime.timedelta(days=10),
        )

        db.add_all([wl_tech, wl_growth, wl_macro])
        db.commit()

        # Add items to Mega-Cap Titans
        tech_symbols = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META"]
        for sym in tech_symbols:
            meta = BASE_UNIVERSE.get(sym, {})
            db.add(WatchlistItem(
                watchlist_id=wl_tech.id,
                symbol=sym,
                custom_notes=f"Core holding: tracking capex and datacenter growth.",
                tags=json.dumps(["MegaCap", meta.get("sector", "Tech")]),
                target_price=round(meta.get("base_price", 100) * 1.15, 2),
                custom_sensitivity="high" if sym in ["NVDA", "TSLA"] else "normal",
            ))

        # Add items to High-Beta Growth
        growth_symbols = ["NVDA", "AMD", "PLTR", "COIN", "TSLA"]
        for sym in growth_symbols:
            meta = BASE_UNIVERSE.get(sym, {})
            db.add(WatchlistItem(
                watchlist_id=wl_growth.id,
                symbol=sym,
                custom_notes="Momentum focus: alert on breakout above 50-DMA.",
                tags=json.dumps(["HighBeta", "Momentum"]),
                target_price=round(meta.get("base_price", 100) * 1.25, 2),
                custom_sensitivity="high",
            ))

        # Add items to Macro
        macro_symbols = ["SPY", "QQQ", "AAPL", "MSFT"]
        for sym in macro_symbols:
            db.add(WatchlistItem(
                watchlist_id=wl_macro.id,
                symbol=sym,
                custom_notes="Hedging and liquidity proxy.",
                tags=json.dumps(["Index", "ETF"]),
                target_price=None,
                custom_sensitivity="low",
            ))

        db.commit()

        # Seed realistic historical visit snapshots for Alex
        # 1. 2 hours 15 minutes ago (Session visit - default comparison)
        prices_2h_ago = {}
        for sym, data in market_service.get_all_tickers().items():
            # simulate price 2h ago slightly different
            mult = 0.965 if sym == "NVDA" else (1.022 if sym == "MSFT" else (0.978 if sym == "TSLA" else 1.002))
            prices_2h_ago[sym] = round(data["price"] * mult, 2)

        snap_midday = UserVisitSnapshot(
            user_id=user_alex.id,
            visit_time=now - datetime.timedelta(hours=2, minutes=15),
            label="Previous Session (2h 15m ago)",
            prices_json=json.dumps(prices_2h_ago),
        )

        # 2. Morning Market Open (5.5 hours ago)
        prices_morning = {}
        for sym, data in market_service.get_all_tickers().items():
            prices_morning[sym] = data.get("open_today", data["price"])

        snap_morning = UserVisitSnapshot(
            user_id=user_alex.id,
            visit_time=now - datetime.timedelta(hours=5, minutes=30),
            label="Market Open (9:30 AM)",
            prices_json=json.dumps(prices_morning),
        )

        # 3. Yesterday Market Close (24 hours ago)
        prices_yesterday = {}
        for sym, data in market_service.get_all_tickers().items():
            prices_yesterday[sym] = data.get("previous_close", data["price"])

        snap_yesterday = UserVisitSnapshot(
            user_id=user_alex.id,
            visit_time=now - datetime.timedelta(days=1),
            label="Yesterday's Close (4:00 PM)",
            prices_json=json.dumps(prices_yesterday),
        )

        db.add_all([snap_midday, snap_morning, snap_yesterday])
        db.commit()

        # Seed some market alerts
        db.add_all([
            MarketAlert(
                symbol="NVDA",
                alert_type="VOLATILITY_BREAKOUT",
                severity="HIGH",
                headline="NVDA surged +3.8% on 2.4x volume following AI accelerator demand forecast revisions.",
                details="Breakout confirmed above short-term consolidation resistance at $126.50.",
                timestamp=now - datetime.timedelta(minutes=45),
            ),
            MarketAlert(
                symbol="MSFT",
                alert_type="LEVEL_CROSS",
                severity="MEDIUM",
                headline="MSFT breached below its 50-day moving average ($425.10).",
                details="Broader software sector compression pulling multiple large caps lower.",
                timestamp=now - datetime.timedelta(minutes=75),
            ),
            MarketAlert(
                symbol="TSLA",
                alert_type="VOLUME_SURGE",
                severity="HIGH",
                headline="TSLA relative volume (RVOL) reached 2.8x daily average.",
                details="Heavy institutional block trading registered ahead of robotaxi milestone.",
                timestamp=now - datetime.timedelta(minutes=30),
            )
        ])
        db.commit()
        print("Database successfully seeded.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
