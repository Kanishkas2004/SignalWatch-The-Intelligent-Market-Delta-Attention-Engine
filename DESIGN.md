# Design Document — Nexus Pulse (SignalWatch)

**Product:** Nexus Pulse — Context-Aware Smart Market Watchlist  
**Repo name:** SignalWatch — The Intelligent Market Delta Attention Engine  
**Audience:** Product reviewers, engineers, and evaluators who need the *why* behind the product

---

## 1. Problem statement

Investors do not experience markets as a continuous tape. They experience them as **intermittent visits**. Between visits, price, volume, and regime can change dramatically — yet nearly every retail watchlist surfaces the same context-free 1-day % change.

### Failure mode of traditional watchlists

| User reality | What the UI shows | What is hidden |
|---|---|---|
| Last checked 10:00 AM, returns 3:00 PM | `AAPL +0.4%` (1D) | −3.8% crash then recovery while away |
| Quiet day vs catalyst day | Same % presentation | 4× RVOL on FDA / earnings / analyst action |
| Technical break during absence | Flat card | Crossed 50-DMA / 200-DMA / 52W level |

**Core insight:** The unit of analysis should be **“since your last visit”**, not “since yesterday’s close.”

---

## 2. Product thesis

Nexus Pulse is an **attention triage cockpit**, not a quote board.

It optimizes for:

1. **Temporal honesty** — every primary signal is relative to the user’s last known visit snapshot.
2. **Statistical meaning** — moves are scored against volatility, volume baselines, and technical levels.
3. **Narrative compression** — a single executive digest replaces scanning 20 identical green/red rows.
4. **Evaluability** — the Time Machine lets judges *simulate* absence so the intelligence is demoable on demand.

### Success criteria

- A returning user can answer “what matters?” in **under 10 seconds**.
- Priority items always include **at least one human-readable reason**.
- Simulated and live modes never lie about data health status.

---

## 3. What information to surface

### 3.1 “While You Were Away” executive digest

Synthesizes the whole watchlist into:

- Elapsed time since last visit (humanized)
- Counts by tier (Priority / Noteworthy / Steady)
- Headline summary sentence
- Top actionable bullets (symbol, price, visit-delta, top reason)
- Sector pulse map

### 3.2 Per-ticker temporal delta

Every card shows:

- Standard 1D change (familiar baseline)
- **Visit-relative delta** (e.g. `⏱️ +4.12% since 12:45 PM`)
- Attention score + tier chip
- Reason chips (Z-score, RVOL, MA cross, catalyst, decoupling)

### 3.3 Time Machine simulator

Controls:

- Continuous slider (~15m → 24h+)
- Presets: 30m ago, 2.2h ago, Market Open, Yesterday Close
- “Bookmark Now” to record a real session reference

Purpose: make temporal intelligence **demo-proof** without waiting hours between visits.

### 3.4 Deep-dive drawer + visit benchmark

Canvas chart overlays a **golden dashed line** at the price captured when the user last visited, so the eye sees “then vs now” without reading numbers first.

---

## 4. Scoring design (Attention Urgency Score)

### 4.1 Composite model

```text
Score ≈ VisitΔ + Volatility(Z) + Volume(RVOL) + Technical + Catalyst/Decoupling
Score ∈ [0, 100]
Sensitivity multiplier: high ×1.25 · normal ×1.0 · low ×0.80
```

### 4.2 Dimension rationale

| Dimension | Why it matters | Design note |
|---|---|---|
| Visit delta | Directly encodes “what changed for *you*” | Primary differentiator vs traditional apps |
| Z-score | Distinguishes 2% moves in KO vs NVDA | Uses ticker volatility as expected σ |
| RVOL | Volume precedes / confirms narrative moves | Approximates intraday expected volume |
| Technical | Regime breaks change risk posture | Detects crosses relative to visit price |
| Catalyst / decoupling | Explains *why* and catches idiosyncratic alpha | Sector avg move as benchmark |

### 4.3 Tier thresholds

Chosen for demo clarity and cognitive load:

- **≥ 60 PRIORITY** — interrupt the user
- **32–59 NOTEWORTHY** — scan when time allows
- **< 32 STEADY** — safe to ignore

Thresholds are product parameters, not sacred constants; they can be tuned per persona via `custom_sensitivity`.

### 4.4 Explanation-first principle

A score without a reason is noise. The engine always emits `reasons[]` in plain English so the UI never shows a red badge without causality.

---

## 5. Persistence & identity design

### Multi-user personas (demo)

Switching personas shows that:

- Watchlists are personal
- Visit snapshots are personal
- Intelligence is session-relative, not global

### Visit snapshots

Each snapshot stores:

- `visit_time`
- `label`
- `prices_json` — `{ symbol: price }` at that moment

Analysis compares **current market_service prices** against the chosen snapshot. If none is selected, the most recent historical snapshot is used.

### Watchlist items

Support:

- Notes and tags
- Optional target price
- Per-symbol sensitivity (`high` / `normal` / `low`)

---

## 6. Handling stale, delayed, or conflicting data

### 4-tier data health matrix

| Status | Meaning | UX |
|---|---|---|
| `LIVE` | Fresh simulated/streamed tick | Green live badge |
| `DELAYED` | Exchange delay class feed | Amber delayed badge |
| `STALE` | No update beyond threshold (~60s) | Warning badge |
| `SIMULATED` | Off-hours / synthetic continuity | Explicit simulated label |

### Resilience

- WebSocket client uses reconnect with backoff
- UI remains usable on REST alone if WS drops
- Health endpoint reports connection count and feed mode

---

## 7. Scalability design (pattern, even in a demo)

**Problem:** Naïve `N users × M stocks` external polling explodes.

**Pattern used:** Decoupled **Market Aggregator**

1. Maintain one in-memory state object per unique symbol
2. Background loop ticks a subset of active symbols
3. Subscribers (WS broadcaster) receive only changed ticks
4. Intelligence scoring runs on demand per watchlist analysis request (not per tick for every user)

This keeps the demo honest about architecture while remaining a single process.

---

## 8. Complexity budget

| Keep simple | Add complexity where it matters |
|---|---|
| FastAPI + SQLite + vanilla SPA | Multi-dimensional anomaly math |
| No npm build / no React | Executive narrative synthesis |
| Simulated market feed | Time Machine snapshot calibration |
| Single deployable process | Visit-relative technical cross detection |

---

## 9. UX principles

1. **Triage before detail** — digest and tiers first; drawer second
2. **Always show “since when”** — never orphan a delta from its reference time
3. **Reasons over icons** — icons may decorate; text must explain
4. **Demo the thesis** — Time Machine is a first-class control, not a hidden debug tool
5. **Honest data health** — never imply institutional live tape when simulating

---

## 10. Non-goals (v1)

- Brokerage order entry / portfolio PnL accounting
- Production licensed market-data ingestion
- Multi-tenant auth / OAuth
- Mobile-native clients
- Full backtesting / portfolio optimization

v1 proves the **attention + temporal delta** thesis end-to-end.

---

## 11. Evaluation checklist (for judges / reviewers)

- [ ] Switch persona → different watchlists load
- [ ] Run Time Machine “2h ago” → visit deltas and digest recalculate
- [ ] Priority names include concrete reasons (σ, RVOL, MA, catalyst)
- [ ] Open deep-dive → visit benchmark line visible
- [ ] Kill/reconnect network briefly → WS badge recovers
- [ ] Add a custom ticker → appears in analysis
- [ ] Bookmark Now → new snapshot selectable

---

## 12. Future design extensions

- Pluggable live feed adapter (Yahoo / Polygon / broker WS) behind `MarketDataService`
- User-tunable dimension weights and tier thresholds
- Push notifications when Priority score crosses threshold between visits
- Cross-device snapshot sync via authenticated API
- Sector heatmaps driven by `sector_pulse`

See **[ARCHITECTURE.md](./ARCHITECTURE.md)** for how these hooks map onto modules.
