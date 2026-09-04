# SignalWatch / Nexus Pulse

### The Intelligent Market Delta Attention Engine

> **"Don't build the obvious watchlist. Build the version you believe should exist — and be ready to explain why."**

**Nexus Pulse** (product name) is an intelligence-first smart market watchlist that eliminates financial noise and cognitive overload. Instead of showing a static 1-day percentage like traditional apps (`+0.4%`), it **remembers when you last visited** and evaluates **five statistical dimensions** — move magnitude during your absence, volatility Z-scores, relative volume, technical regime breaks, and sector decoupling — then triages what deserves your attention.

Repository: [SignalWatch-The-Intelligent-Market-Delta-Attention-Engine](https://github.com/Kanishkas2004/SignalWatch-The-Intelligent-Market-Delta-Attention-Engine)

---

## Why this exists

Traditional watchlists (Apple Stocks, TradingView, Robinhood) treat markets as **static daily snapshots with zero temporal context**.

If an investor checks their watchlist at 3:00 PM having last logged in at 10:00 AM, those apps still show a bland 1-day change. That conceals whether the stock crashed −4% and rebounded while they were away, whether volume is 4× normal on a catalyst, or whether price broke a 50-day moving average during their absence.

**Nexus Pulse answers two questions immediately:**

1. *What meaningfully changed since you were last here?*
2. *What deserves your attention right now, and why?*

---

## Product thesis: what counts as a “meaningful change”?

A stock moving ±1% is not inherently meaningful. The engine computes a multi-dimensional **Attention Urgency Score (0–100)** and groups tickers into three triage tiers.

### Five dimensions of meaningful change

| Dimension | Quantitative metric | Signal threshold | Weight |
|---|---|---|---|
| **1. Temporal Delta (Δ_visit)** | `(P_now − P_visit) / P_visit × 100` | \|Δ\| ≥ 1.5% since last visit | 25% |
| **2. Volatility Anomaly (Z-score)** | `Z = \|P_now − P_open\| / (P_open · σ_20D)` | Z ≥ 2.0σ | 25% |
| **3. Volume Anomaly (RVOL)** | `RVOL = Current Volume / Expected Volume(t)` | RVOL ≥ ~1.8–2.0× | 20% |
| **4. Technical Regime Breaks** | 50-DMA, 200-DMA, 52W High/Low | Crossed while user was away | 15% |
| **5. Catalyst & Sector Decoupling** | \|ΔP_stock − ΔP_sector\| | Decoupled ≥ ~2.0–2.2% or active news | 15% |

### Attention tiers

| Tier | Score | Meaning |
|---|---|---|
| 🔴 **PRIORITY** | ≥ 60 | Major catalyst, heavy volume surge, or ≥2σ breakout since last visit |
| 🟡 **NOTEWORTHY** | 32–59 | Moderate move, MA test, or elevated order flow |
| 🟢 **STEADY** | < 32 | In-line with expected noise; minimal cognitive load |

---

## Key features

- **“While You Were Away” executive digest** — plain-English briefing of what mattered across the watchlist during your absence
- **Temporal price delta on every ticker** — both 1D change and change since your previous session
- **Interactive Time Machine** — slider/presets (15m → 24h, Market Open, Yesterday Close) to simulate leaving and returning; deltas recalculate live
- **Deep-dive charts** — visit benchmark as a golden dashed reference line on Canvas charts
- **Multi-persona demos** — Alex Reed (Tech Momentum), Elena Rostova (Macro), Sam Vance (AI Specialist)
- **Named watchlists** — Mega-Cap Titans, High-Beta Growth, Macro & Benchmarks, plus custom lists
- **Live WebSocket tick stream** — simulated GBM + jump diffusion with optimistic reconnect
- **4-tier data health** — `LIVE` · `DELAYED` · `STALE` · `SIMULATED`

---

## Architecture at a glance

```text
Browser (Vanilla ES6 SPA)
    │  REST + WebSocket
    ▼
FastAPI (backend/main.py)
    ├── Intelligence Engine  → Attention Score + Executive Digest
    ├── Market Data Service  → Universe, ticks, sector benchmarks
    ├── SQLite / SQLAlchemy  → Users, watchlists, visit snapshots
    └── Static frontend      → / and /static/*
```

Full system design, scoring math, data model, and diagrams:

- **[DESIGN.md](./DESIGN.md)** — product design, UX decisions, scoring rationale
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** — component architecture, data flow, API surface, ER diagram

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| API | FastAPI + Uvicorn | Async, typed, OpenAPI docs out of the box |
| Persistence | SQLite + SQLAlchemy | Zero-ops local demos; visit snapshots & multi-user personas |
| Market feed | In-process simulator | Works nights/weekends; GBM + Poisson-style jumps |
| Frontend | Vanilla ES6 + Tailwind CDN | No build step, instant launch |
| Charts | Canvas (`frontend/js/charts.js`) | Lightweight deep-dive overlays |
| Realtime | WebSocket `/ws/live` | Delta-only tick broadcast |

---

## Project structure

```text
smart_market_watchlist/
├── run.py                      # Uvicorn entrypoint → http://localhost:8000
├── requirements.txt
├── README.md
├── DESIGN.md
├── ARCHITECTURE.md
├── backend/
│   ├── main.py                 # FastAPI app, REST + WS routes
│   ├── intelligence_engine.py  # 5-dimension attention scoring + digest
│   ├── market_service.py       # Universe + tick simulation loop
│   ├── database.py             # SQLAlchemy models
│   ├── models.py               # Pydantic API schemas
│   ├── seed_data.py            # Demo users, watchlists, snapshots
│   └── seed helpers / __init__
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── app.js              # App state & UI orchestration
│       ├── websocket.js        # Live feed + reconnect
│       ├── time_machine.js     # Temporal simulation controls
│       └── charts.js           # Deep-dive Canvas charts
└── tests/
    ├── test_intelligence.py    # Scoring / tier / digest unit tests
    └── test_api.py             # API smoke tests
```

---

## Getting started

### Prerequisites

- Python **3.10+** (tested through newer 3.x)

### Install & run

```bash
# Clone
git clone https://github.com/Kanishkas2004/SignalWatch-The-Intelligent-Market-Delta-Attention-Engine.git
cd SignalWatch-The-Intelligent-Market-Delta-Attention-Engine

# Virtual environment (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Dependencies
pip install -r requirements.txt
pip install pytest   # for tests (optional)

# Start
python run.py
```

Open:

- App: **http://localhost:8000**
- Interactive API docs: **http://localhost:8000/docs**

### Tests

```bash
.\.venv\Scripts\python -m pytest tests -q
```

---

## API reference (high level)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Service health, WS count, feed status |
| `GET` | `/api/users` | Demo user personas |
| `GET` | `/api/users/{id}/watchlists` | Watchlists for a user |
| `POST` | `/api/users/{id}/watchlists` | Create watchlist (+ optional symbols) |
| `DELETE` | `/api/watchlists/{id}` | Delete watchlist |
| `POST` | `/api/watchlists/{id}/items` | Add ticker (notes, tags, sensitivity) |
| `DELETE` | `/api/watchlists/{id}/items/{item_id}` | Remove ticker |
| `GET` | `/api/watchlists/{id}/analysis` | **Primary intelligence endpoint** — scores, deltas, digest |
| `GET` | `/api/users/{id}/snapshots` | Visit bookmarks |
| `POST` | `/api/users/{id}/snapshots/record` | Bookmark current prices |
| `POST` | `/api/users/{id}/snapshots/simulate` | Time Machine: simulate return after N minutes |
| `GET` | `/api/tickers/search?q=` | Ticker autocomplete |
| `GET` | `/api/tickers/{symbol}/detail` | Quote + sparkline + bars + catalysts |
| `GET` | `/api/alerts` | Recent market alerts |
| `WS` | `/ws/live` | Real-time tick stream (`TICK_UPDATE`, `PING`/`PONG`) |

---

## Demo personas (seeded)

| Persona | Focus | Sample watchlists |
|---|---|---|
| **Alex Reed** | Tech Momentum Trader | Mega-Cap Titans, High-Beta Growth & AI, Macro & Benchmarks |
| **Elena Rostova** | Macro & Value Strategist | Macro-oriented lists |
| **Sam Vance** | Semiconductor & AI Specialist | AI / semis concentration |

On first boot, `seed_data.py` creates users, watchlists, historical visit snapshots, and sample alerts so the “while you were away” experience works immediately.

---

## Design decisions (summary)

| Area | Decision |
|---|---|
| Surface | Digest + temporal delta + Time Machine + visit-benchmark charts |
| Persistence | SQLite for users, watchlists, visit price snapshots |
| Stale / delayed data | Explicit `LIVE` / `DELAYED` / `STALE` / `SIMULATED` badges |
| Scale pattern | Single aggregator subscription per unique ticker; in-memory stats; delta WS push |
| Complexity budget | Keep stack simple; put complexity in anomaly math + narrative synthesis |

Details and rationale: **[DESIGN.md](./DESIGN.md)**.

---

## License & disclaimer

This project is a **demonstration / portfolio intelligence engine**. Market prices are primarily **simulated** for continuous demo reliability. It is **not** investment advice and should not be used as a production trading system without a licensed market-data feed and compliance review.

---

## Related docs

| Doc | Contents |
|---|---|
| [DESIGN.md](./DESIGN.md) | Product thesis, UX, scoring, data-health, trade-offs |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Component diagram, request/tick flows, ER model, module map |
