import datetime
from typing import Dict, List, Any, Optional, Tuple
from backend.models import AttentionDetail, TickerAnalysis, ExecutiveDigest


class IntelligenceEngine:
    def __init__(self):
        pass

    def compute_ticker_attention(
        self,
        ticker_data: Dict[str, Any],
        price_at_visit: Optional[float],
        sector_benchmarks: Dict[str, float],
        custom_sensitivity: str = "normal",
    ) -> AttentionDetail:
        """
        Calculates multi-dimensional attention score (0-100), tier, and
        plain-English causality explanations.
        """
        current_price = ticker_data["price"]
        prev_close = ticker_data["previous_close"]
        open_price = ticker_data.get("open_today", prev_close)
        volat = ticker_data.get("volatility", 0.02)
        volume = ticker_data.get("volume", 0)
        avg_vol = ticker_data.get("avg_volume", 1)
        sma_50 = ticker_data.get("sma_50", current_price)
        sma_200 = ticker_data.get("sma_200", current_price)
        high_52w = ticker_data.get("high_52w", current_price * 1.5)
        low_52w = ticker_data.get("low_52w", current_price * 0.5)
        sector = ticker_data.get("sector", "Other")

        reasons: List[str] = []
        score_components = {
            "visit_delta": 0.0,
            "volatility": 0.0,
            "volume": 0.0,
            "technical": 0.0,
            "catalyst": 0.0,
        }

        # 1. Delta Since Last Visit
        if price_at_visit is not None and price_at_visit > 0:
            delta_visit_pct = ((current_price - price_at_visit) / price_at_visit) * 100.0
            abs_delta = abs(delta_visit_pct)
            if abs_delta >= 3.0:
                score_components["visit_delta"] = 30.0
                direction = "surged" if delta_visit_pct > 0 else "slumped"
                reasons.append(f"⏱️ {direction.capitalize()} {delta_visit_pct:+.2f}% since you last checked.")
            elif abs_delta >= 1.5:
                score_components["visit_delta"] = 18.0
                direction = "up" if delta_visit_pct > 0 else "down"
                reasons.append(f"⏱️ Moved {direction} {delta_visit_pct:+.2f}% while you were away.")
            elif abs_delta >= 0.75:
                score_components["visit_delta"] = 8.0
        else:
            # Fallback to today's change if no prior visit price
            delta_visit_pct = ((current_price - prev_close) / prev_close) * 100.0

        # 2. Statistical Volatility (Z-score relative to expected intraday sigma)
        expected_sigma = volat
        actual_move_pct = abs((current_price - open_price) / open_price)
        z_score = actual_move_pct / expected_sigma if expected_sigma > 0 else 0.0
        z_score = round(z_score, 2)

        if z_score >= 3.0:
            score_components["volatility"] = 25.0
            reasons.append(f"🚨 Extreme {z_score:.1f}σ statistical volatility outlier today.")
        elif z_score >= 2.0:
            score_components["volatility"] = 18.0
            reasons.append(f"⚡ Notable {z_score:.1f}σ move beyond normal volatility range.")
        elif z_score >= 1.2:
            score_components["volatility"] = 8.0

        # 3. Volume Anomaly (RVOL)
        rvol = volume / (avg_vol * 0.75) if avg_vol > 0 else 1.0  # approximate intraday expectation
        rvol = round(rvol, 2)

        if rvol >= 2.5:
            score_components["volume"] = 20.0
            reasons.append(f"📊 Heavy institutional volume surge ({rvol:.1f}x normal RVOL).")
        elif rvol >= 1.8:
            score_components["volume"] = 12.0
            reasons.append(f"📊 Elevated volume running at {rvol:.1f}x average.")
        elif rvol >= 1.3:
            score_components["volume"] = 6.0

        # 4. Technical Regime Crossings
        crossed_sma50 = False
        crossed_sma200 = False
        crossed_52w_high = False
        crossed_52w_low = False

        if price_at_visit is not None:
            # Crossed 50 DMA
            if (price_at_visit < sma_50 <= current_price) or (price_at_visit > sma_50 >= current_price):
                crossed_sma50 = True
                verdict = "above" if current_price >= sma_50 else "below"
                reasons.append(f"📉 Crossed {verdict} 50-day moving average (${sma_50:.2f}).")
                score_components["technical"] += 8.0

            # Crossed 200 DMA
            if (price_at_visit < sma_200 <= current_price) or (price_at_visit > sma_200 >= current_price):
                crossed_sma200 = True
                verdict = "above" if current_price >= sma_200 else "below"
                reasons.append(f"📉 Major regime test: crossed {verdict} 200-day moving average (${sma_200:.2f}).")
                score_components["technical"] += 10.0

        # 52-week High / Low test
        if current_price >= high_52w * 0.995:
            crossed_52w_high = True
            reasons.append(f"🚀 Trading at/near fresh 52-week high (${high_52w:.2f}).")
            score_components["technical"] += 7.0
        elif current_price <= low_52w * 1.005:
            crossed_52w_low = True
            reasons.append(f"⚠️ Testing critical 52-week low support (${low_52w:.2f}).")
            score_components["technical"] += 7.0

        score_components["technical"] = min(15.0, score_components["technical"])

        # 5. Catalyst & Sector Decoupling
        sector_move = sector_benchmarks.get(sector, 0.0)
        stock_move_pct = ((current_price - prev_close) / prev_close) * 100.0
        sector_divergence = stock_move_pct - sector_move
        catalyst_texts = [c["headline"] for c in ticker_data.get("catalysts", [])]

        if catalyst_texts:
            score_components["catalyst"] += 8.0
            reasons.append(f"📰 Catalyst: {catalyst_texts[0]}")

        if abs(sector_divergence) >= 2.2:
            score_components["catalyst"] += 7.0
            direction = "outperforming" if sector_divergence > 0 else "underperforming"
            reasons.append(f"🔀 Decoupling from {sector} sector ({direction} by {abs(sector_divergence):.1f}%).")

        score_components["catalyst"] = min(15.0, score_components["catalyst"])

        # Composite raw score
        raw_score = sum(score_components.values())

        # Sensitivity weighting
        if custom_sensitivity == "high":
            raw_score *= 1.25
        elif custom_sensitivity == "low":
            raw_score *= 0.80

        composite_score = round(min(100.0, max(0.0, raw_score)), 1)

        # Tier assignment
        if composite_score >= 60.0:
            tier = "PRIORITY"
        elif composite_score >= 32.0:
            tier = "NOTEWORTHY"
        else:
            tier = "STEADY"

        if not reasons:
            reasons.append("Quiet session: Trading within expected intraday bounds.")

        return AttentionDetail(
            composite_score=composite_score,
            tier=tier,
            reasons=reasons,
            delta_since_visit_pct=round(delta_visit_pct, 2),
            price_at_visit=price_at_visit,
            z_score=z_score,
            rvol=rvol,
            crossed_sma50=crossed_sma50,
            crossed_sma200=crossed_sma200,
            crossed_52w_high=crossed_52w_high,
            crossed_52w_low=crossed_52w_low,
            sector_divergence_pct=round(sector_divergence, 2),
            catalysts=catalyst_texts,
        )

    def analyze_ticker(
        self,
        ticker_data: Dict[str, Any],
        price_at_visit: Optional[float],
        sector_benchmarks: Dict[str, float],
        custom_sensitivity: str = "normal",
    ) -> TickerAnalysis:
        attention = self.compute_ticker_attention(
            ticker_data, price_at_visit, sector_benchmarks, custom_sensitivity
        )
        current_price = ticker_data["price"]
        prev_close = ticker_data["previous_close"]
        change = round(current_price - prev_close, 2)
        change_pct = round((change / prev_close) * 100.0, 2)

        return TickerAnalysis(
            symbol=ticker_data["symbol"],
            company_name=ticker_data["name"],
            sector=ticker_data["sector"],
            price=current_price,
            change_today=change,
            change_today_pct=change_pct,
            high_today=ticker_data["high_today"],
            low_today=ticker_data["low_today"],
            volume=ticker_data["volume"],
            avg_volume=ticker_data["avg_volume"],
            high_52w=ticker_data["high_52w"],
            low_52w=ticker_data["low_52w"],
            sma_50=ticker_data["sma_50"],
            sma_200=ticker_data["sma_200"],
            attention=attention,
            data_health=ticker_data.get("data_health", "LIVE"),
            latency_ms=ticker_data.get("latency_ms", 25),
            last_updated=ticker_data.get("last_updated", datetime.datetime.utcnow()),
            sparkline_1d=ticker_data.get("sparkline_1d", []),
            historical_bars=ticker_data.get("historical_bars", []),
        )

    def generate_executive_digest(
        self,
        analyzed_tickers: List[TickerAnalysis],
        last_visit_time: datetime.datetime,
        sector_benchmarks: Dict[str, float],
    ) -> ExecutiveDigest:
        """
        Synthesizes the entire watchlist state into an intelligent narrative
        executive summary for when the user returns.
        """
        now = datetime.datetime.utcnow()
        elapsed = now - last_visit_time
        total_seconds = max(1, int(elapsed.total_seconds()))

        # Human-readable elapsed string
        if total_seconds < 60:
            duration_text = "few moments"
            elapsed_text = "Just moments ago"
        elif total_seconds < 3600:
            mins = total_seconds // 60
            duration_text = f"{mins}m"
            elapsed_text = f"{mins} minute{'s' if mins != 1 else ''} ago"
        elif total_seconds < 86400:
            hrs = total_seconds // 3600
            mins = (total_seconds % 3600) // 60
            duration_text = f"{hrs}h {mins}m"
            elapsed_text = f"{hrs}h {mins}m ago"
        else:
            days = total_seconds // 86400
            duration_text = f"{days}d"
            elapsed_text = f"{days} day{'s' if days != 1 else ''} ago"

        priority_items = [t for t in analyzed_tickers if t.attention.tier == "PRIORITY"]
        noteworthy_items = [t for t in analyzed_tickers if t.attention.tier == "NOTEWORTHY"]
        steady_items = [t for t in analyzed_tickers if t.attention.tier == "STEADY"]

        # Sort priority by attention score descending
        sorted_movers = sorted(analyzed_tickers, key=lambda x: x.attention.composite_score, reverse=True)

        # Headline summary
        total = len(analyzed_tickers)
        if len(priority_items) > 0:
            headline = f"Welcome back. In the {duration_text} since your last visit, {len(priority_items)} of your {total} stocks require priority attention."
        elif len(noteworthy_items) > 0:
            headline = f"Markets were moderately active while you were away: {len(noteworthy_items)} noteworthy movements detected across your watchlist."
        else:
            headline = f"All quiet across your watchlist in the {duration_text} since your last check. No major catalysts or level breaches."

        # Actionable bullet points
        action_bullets: List[str] = []
        for item in sorted_movers[:4]:
            top_reason = item.attention.reasons[0] if item.attention.reasons else "Normal price action"
            delta_str = f"{item.attention.delta_since_visit_pct:+.2f}% since visit"
            bullet = f"**{item.symbol}** (${item.price:.2f}, {delta_str}): {top_reason}"
            action_bullets.append(bullet)

        return ExecutiveDigest(
            last_visit_time=last_visit_time,
            elapsed_text=elapsed_text,
            total_watched=total,
            priority_count=len(priority_items),
            noteworthy_count=len(noteworthy_items),
            steady_count=len(steady_items),
            headline_summary=headline,
            action_bullets=action_bullets,
            sector_pulse=sector_benchmarks,
        )


intelligence_engine = IntelligenceEngine()
