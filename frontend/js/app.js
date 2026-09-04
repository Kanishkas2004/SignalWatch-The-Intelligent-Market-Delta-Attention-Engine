/**
 * Nexus Pulse - Main Application Controller
 */

class NexusPulseApp {
  constructor() {
    this.currentUserId = 1;
    this.currentWatchlistId = null;
    this.users = [];
    this.watchlists = [];
    this.tickers = [];
    this.tickersMap = {};
    this.activeViewMode = "triage"; // "triage" | "all" | "sector"
    this.timeMachine = new TimeMachineController(this);
    this.selectedTicker = null;
    this.searchDebounce = null;
  }

  async init() {
    this.bindEvents();
    this.setupLiveFeed();
    await this.loadUsers();
    await this.loadWatchlists();
    await this.timeMachine.loadSnapshots(this.currentUserId);
    await this.loadWatchlistAnalysis();
  }

  setupLiveFeed() {
    window.liveFeed.onStatusChange((status) => {
      const badge = document.getElementById("connection-badge");
      if (!badge) return;
      if (status === "LIVE") {
        badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400 mr-2 animate-pulse"></span>LIVE FEED`;
        badge.className = "flex items-center text-xs font-mono px-2.5 py-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-400";
      } else if (status === "CONNECTING") {
        badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-amber-400 mr-2 animate-pulse"></span>CONNECTING`;
        badge.className = "flex items-center text-xs font-mono px-2.5 py-1 rounded-full border border-amber-500/30 bg-amber-500/10 text-amber-400";
      } else {
        badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-rose-400 mr-2"></span>OFFLINE`;
        badge.className = "flex items-center text-xs font-mono px-2.5 py-1 rounded-full border border-rose-500/30 bg-rose-500/10 text-rose-400";
      }
    });

    window.liveFeed.onTicks((ticks) => {
      ticks.forEach((tick) => {
        this.handleLiveTick(tick);
      });
    });

    window.liveFeed.connect();
  }

  handleLiveTick(tick) {
    const sym = tick.symbol;
    const existing = this.tickersMap[sym];
    if (!existing) return;

    // Update memory model
    const oldPrice = existing.price;
    existing.price = tick.price;
    existing.change_today = tick.change_today;
    existing.change_today_pct = tick.change_today_pct;
    existing.volume = tick.volume;

    // Recalculate delta since visit
    if (existing.attention.price_at_visit) {
      existing.attention.delta_since_visit_pct = +(
        ((tick.price - existing.attention.price_at_visit) / existing.attention.price_at_visit) * 100
      ).toFixed(2);
    }

    // Append to sparkline
    if (!existing.sparkline_1d) existing.sparkline_1d = [];
    existing.sparkline_1d.push(tick.price);
    if (existing.sparkline_1d.length > 50) existing.sparkline_1d.shift();

    // Flash price element on card
    const priceEl = document.getElementById(`price-${sym}`);
    const cardEl = document.getElementById(`card-${sym}`);
    const visitDeltaEl = document.getElementById(`visit-delta-${sym}`);
    const changeTodayEl = document.getElementById(`change-today-${sym}`);

    if (priceEl) {
      priceEl.textContent = `$${tick.price.toFixed(2)}`;
    }

    if (visitDeltaEl && existing.attention.price_at_visit) {
      const d = existing.attention.delta_since_visit_pct;
      visitDeltaEl.textContent = `${d >= 0 ? "+" : ""}${d.toFixed(2)}% since visit`;
      visitDeltaEl.className = `text-xs font-mono font-medium ${d >= 0 ? "text-emerald-400" : "text-rose-400"}`;
    }

    if (changeTodayEl) {
      const c = tick.change_today_pct;
      changeTodayEl.textContent = `${c >= 0 ? "+" : ""}${c.toFixed(2)}%`;
      changeTodayEl.className = `text-xs font-mono ${c >= 0 ? "text-emerald-400" : "text-rose-400"}`;
    }

    if (cardEl) {
      cardEl.classList.remove("tick-flash-up", "tick-flash-down");
      void cardEl.offsetWidth; // Force reflow
      cardEl.classList.add(tick.direction === "UP" ? "tick-flash-up" : "tick-flash-down");
    }

    // Update mini sparkline
    const sparkCanvas = document.getElementById(`sparkline-${sym}`);
    if (sparkCanvas) {
      window.ChartEngine.drawSparkline(
        sparkCanvas,
        existing.sparkline_1d,
        existing.change_today_pct >= 0
      );
    }

    // If detail drawer is open for this ticker, update drawer
    if (this.selectedTicker && this.selectedTicker.symbol === sym) {
      this.renderDrawer(existing);
    }
  }

  async loadUsers() {
    try {
      const res = await fetch("/api/users");
      if (res.ok) {
        this.users = await res.json();
        const select = document.getElementById("user-select");
        if (select) {
          select.innerHTML = "";
          this.users.forEach((u) => {
            const opt = document.createElement("option");
            opt.value = u.id;
            opt.textContent = `${u.display_name} (${u.persona})`;
            select.appendChild(opt);
          });
          select.value = this.currentUserId;
        }
      }
    } catch (err) {
      console.error("Failed to load users:", err);
    }
  }

  async loadWatchlists() {
    try {
      const res = await fetch(`/api/users/${this.currentUserId}/watchlists`);
      if (res.ok) {
        this.watchlists = await res.json();
        const select = document.getElementById("watchlist-select");
        if (select) {
          select.innerHTML = "";
          this.watchlists.forEach((w) => {
            const opt = document.createElement("option");
            opt.value = w.id;
            opt.textContent = w.name;
            if (w.is_default && !this.currentWatchlistId) {
              this.currentWatchlistId = w.id;
              opt.selected = true;
            }
            select.appendChild(opt);
          });
          if (!this.currentWatchlistId && this.watchlists.length > 0) {
            this.currentWatchlistId = this.watchlists[0].id;
          }
          if (this.currentWatchlistId) {
            select.value = this.currentWatchlistId;
          }
        }
      }
    } catch (err) {
      console.error("Failed to load watchlists:", err);
    }
  }

  async loadWatchlistAnalysis() {
    if (!this.currentWatchlistId) return;

    this.showLoading(true);
    try {
      let url = `/api/watchlists/${this.currentWatchlistId}/analysis`;
      if (this.timeMachine.activeSnapshotId) {
        url += `?snapshot_id=${this.timeMachine.activeSnapshotId}`;
      }

      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        this.tickers = data.tickers;
        this.tickersMap = {};
        this.tickers.forEach((t) => {
          this.tickersMap[t.symbol] = t;
        });

        // Set comparison snapshot label
        const snapLabelEl = document.getElementById("current-snapshot-label");
        if (snapLabelEl) {
          snapLabelEl.textContent = data.comparison_snapshot.label;
        }

        this.renderExecutiveDigest(data.executive_digest);
        this.renderWatchlist();
      }
    } catch (err) {
      console.error("Failed to load watchlist analysis:", err);
    } finally {
      this.showLoading(false);
    }
  }

  renderExecutiveDigest(digest) {
    const container = document.getElementById("executive-digest-container");
    if (!container) return;

    const priorityBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-semibold badge-priority">🔴 ${digest.priority_count} Priority Actions</span>`;
    const noteworthyBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-semibold badge-noteworthy">🟡 ${digest.noteworthy_count} Noteworthy</span>`;
    const steadyBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-semibold badge-steady">🟢 ${digest.steady_count} Steady</span>`;

    let bulletsHtml = digest.action_bullets
      .map(
        (b) =>
          `<li class="flex items-start space-x-2 text-sm text-slate-300">
            <span class="text-cyan-400 mt-0.5">✦</span>
            <span>${b.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')}</span>
          </li>`
      )
      .join("");

    // Sector pulse pill tags
    let sectorPills = Object.entries(digest.sector_pulse || {})
      .map(([sec, move]) => {
        const isUp = move >= 0;
        return `<div class="px-2.5 py-1 rounded bg-slate-800/80 border border-slate-700/60 text-xs flex items-center space-x-1.5">
          <span class="text-slate-400">${sec}:</span>
          <span class="font-mono font-medium ${isUp ? "text-emerald-400" : "text-rose-400"}">${isUp ? "+" : ""}${move.toFixed(2)}%</span>
        </div>`;
      })
      .join("");

    container.innerHTML = `
      <div class="glass-panel p-6 border-l-4 border-l-cyan-500 relative overflow-hidden">
        <div class="absolute -right-10 -bottom-10 w-48 h-48 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div class="flex items-center space-x-2">
            <span class="text-xs uppercase tracking-wider font-semibold text-cyan-400 bg-cyan-500/10 px-2.5 py-0.5 rounded border border-cyan-500/20">
              ⚡ Intelligence Briefing
            </span>
            <span class="text-xs text-slate-400">Since your last visit (${digest.elapsed_text})</span>
          </div>
          <div class="flex items-center space-x-2">
            ${priorityBadge}
            ${noteworthyBadge}
            ${steadyBadge}
          </div>
        </div>

        <h2 class="text-lg font-semibold text-white mb-3">
          ${digest.headline_summary}
        </h2>

        <ul class="space-y-2 mb-4 bg-slate-900/40 p-3.5 rounded-lg border border-white/5">
          ${bulletsHtml}
        </ul>

        <div class="pt-2 border-t border-white/5 flex flex-wrap items-center gap-2">
          <span class="text-xs font-medium text-slate-400 mr-1">Sector Heatmap Pulse:</span>
          ${sectorPills}
        </div>
      </div>
    `;
  }

  renderWatchlist() {
    const container = document.getElementById("watchlist-container");
    if (!container) return;

    if (this.tickers.length === 0) {
      container.innerHTML = `
        <div class="text-center py-16 text-slate-400">
          <p class="text-base mb-2">No stocks in this watchlist yet.</p>
          <button onclick="app.openSearchModal()" class="px-4 py-2 text-sm bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-medium transition">
            + Add Your First Stock
          </button>
        </div>
      `;
      return;
    }

    if (this.activeViewMode === "triage") {
      this.renderTriageView(container);
    } else if (this.activeViewMode === "sector") {
      this.renderSectorView(container);
    } else {
      this.renderGridView(container);
    }

    // Render sparklines after elements inserted into DOM
    this.tickers.forEach((t) => {
      const sparkCanvas = document.getElementById(`sparkline-${t.symbol}`);
      if (sparkCanvas && t.sparkline_1d) {
        window.ChartEngine.drawSparkline(
          sparkCanvas,
          t.sparkline_1d,
          t.change_today_pct >= 0
        );
      }
    });
  }

  renderTriageView(container) {
    const priority = this.tickers.filter((t) => t.attention.tier === "PRIORITY");
    const noteworthy = this.tickers.filter((t) => t.attention.tier === "NOTEWORTHY");
    const steady = this.tickers.filter((t) => t.attention.tier === "STEADY");

    // Sort each tier by Attention Score descending
    const sorter = (a, b) => b.attention.composite_score - a.attention.composite_score;
    priority.sort(sorter);
    noteworthy.sort(sorter);
    steady.sort(sorter);

    container.innerHTML = `
      <div class="space-y-8">
        ${
          priority.length > 0
            ? `
          <div>
            <div class="flex items-center space-x-2 mb-3">
              <span class="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse"></span>
              <h3 class="text-sm uppercase tracking-wider font-bold text-rose-400">
                🔴 Priority Attention Required (${priority.length})
              </h3>
              <span class="text-xs text-slate-400">— Critical catalysts, major volume anomalies, or 2σ+ regime breaks</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              ${priority.map((t) => this.renderTickerCard(t)).join("")}
            </div>
          </div>
        `
            : ""
        }

        ${
          noteworthy.length > 0
            ? `
          <div>
            <div class="flex items-center space-x-2 mb-3">
              <span class="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
              <h3 class="text-sm uppercase tracking-wider font-bold text-amber-400">
                🟡 Noteworthy Shifts (${noteworthy.length})
              </h3>
              <span class="text-xs text-slate-400">— Moderate divergence, moving average crossings, or elevated interest</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              ${noteworthy.map((t) => this.renderTickerCard(t)).join("")}
            </div>
          </div>
        `
            : ""
        }

        ${
          steady.length > 0
            ? `
          <div>
            <div class="flex items-center space-x-2 mb-3">
              <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              <h3 class="text-sm uppercase tracking-wider font-bold text-emerald-400">
                🟢 Steady & In-Line (${steady.length})
              </h3>
              <span class="text-xs text-slate-400">— Trading within normal statistical noise bounds</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              ${steady.map((t) => this.renderTickerCard(t)).join("")}
            </div>
          </div>
        `
            : ""
        }
      </div>
    `;
  }

  renderGridView(container) {
    const sorted = [...this.tickers].sort((a, b) => b.attention.composite_score - a.attention.composite_score);
    container.innerHTML = `
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        ${sorted.map((t) => this.renderTickerCard(t)).join("")}
      </div>
    `;
  }

  renderSectorView(container) {
    const groups = {};
    this.tickers.forEach((t) => {
      groups[t.sector] = groups[t.sector] || [];
      groups[t.sector].push(t);
    });

    container.innerHTML = `
      <div class="space-y-8">
        ${Object.entries(groups)
          .map(
            ([sector, list]) => `
          <div>
            <h3 class="text-sm uppercase tracking-wider font-bold text-cyan-400 mb-3 flex items-center space-x-2">
              <span>🏢 ${sector} (${list.length})</span>
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              ${list.map((t) => this.renderTickerCard(t)).join("")}
            </div>
          </div>
        `
          )
          .join("")}
      </div>
    `;
  }

  renderTickerCard(t) {
    const isUpToday = t.change_today_pct >= 0;
    const isUpVisit = t.attention.delta_since_visit_pct >= 0;
    const tierBadgeClass =
      t.attention.tier === "PRIORITY"
        ? "badge-priority"
        : t.attention.tier === "NOTEWORTHY"
        ? "badge-noteworthy"
        : "badge-steady";

    const scoreColor =
      t.attention.composite_score >= 60
        ? "text-rose-400 border-rose-500/40 bg-rose-500/10"
        : t.attention.composite_score >= 32
        ? "text-amber-400 border-amber-500/40 bg-amber-500/10"
        : "text-emerald-400 border-emerald-500/40 bg-emerald-500/10";

    const topReason = t.attention.reasons[0] || "Trading within normal limits";

    return `
      <div id="card-${t.symbol}" onclick="app.openDetailDrawer('${t.symbol}')"
        class="glass-panel p-4 cursor-pointer relative hover:border-cyan-500/40 transition group flex flex-col justify-between">
        
        <!-- Header -->
        <div>
          <div class="flex items-start justify-between mb-2">
            <div>
              <div class="flex items-center space-x-2">
                <span class="text-base font-bold font-mono text-white group-hover:text-cyan-400 transition">${t.symbol}</span>
                <span class="text-xs px-2 py-0.5 rounded-full border ${tierBadgeClass} font-semibold">${t.attention.tier}</span>
              </div>
              <p class="text-xs text-slate-400 truncate max-w-[180px]">${t.company_name}</p>
            </div>
            
            <!-- Attention Score Pill -->
            <div class="flex flex-col items-end">
              <span class="text-xs font-mono font-bold px-2 py-0.5 rounded-md border ${scoreColor}">
                ${t.attention.composite_score.toFixed(0)} / 100
              </span>
              <span class="text-[10px] text-slate-400 mt-0.5">Attention Score</span>
            </div>
          </div>

          <!-- Price & Temporal Delta Section -->
          <div class="flex items-baseline justify-between py-2 border-y border-white/5 my-2">
            <div>
              <div class="text-xl font-bold font-mono text-white" id="price-${t.symbol}">$${t.price.toFixed(2)}</div>
              <div class="text-xs font-mono ${isUpToday ? "text-emerald-400" : "text-rose-400"}" id="change-today-${t.symbol}">
                ${isUpToday ? "+" : ""}${t.change_today_pct.toFixed(2)}% Today
              </div>
            </div>

            <!-- THE MEANINGFUL CHANGE: DELTA SINCE LAST VISIT -->
            <div class="text-right bg-slate-900/60 px-2.5 py-1 rounded border border-white/5">
              <div class="text-[10px] text-slate-400 flex items-center justify-end space-x-1">
                <span>⏱️ Since Last Check</span>
              </div>
              <div class="text-xs font-mono font-bold ${isUpVisit ? "text-emerald-400" : "text-rose-400"}" id="visit-delta-${t.symbol}">
                ${isUpVisit ? "+" : ""}${t.attention.delta_since_visit_pct.toFixed(2)}%
              </div>
            </div>
          </div>

          <!-- Why it matters / Primary Reason -->
          <div class="text-xs text-slate-300 mb-3 line-clamp-2 bg-slate-800/30 p-2 rounded border border-white/5">
            ${topReason}
          </div>
        </div>

        <!-- Sparkline and Indicators Footer -->
        <div class="flex items-center justify-between pt-2 border-t border-white/5 mt-auto">
          <div class="flex items-center space-x-2 text-[11px] font-mono text-slate-400">
            <span>RVOL: <strong class="text-white">${t.attention.rvol.toFixed(1)}x</strong></span>
            <span>•</span>
            <span>Z: <strong class="text-white">${t.attention.z_score.toFixed(1)}σ</strong></span>
          </div>
          <canvas id="sparkline-${t.symbol}" width="90" height="26" class="rounded"></canvas>
        </div>
      </div>
    `;
  }

  openDetailDrawer(symbol) {
    const t = this.tickersMap[symbol];
    if (!t) return;
    this.selectedTicker = t;
    this.renderDrawer(t);
    const drawer = document.getElementById("detail-drawer");
    const backdrop = document.getElementById("drawer-backdrop");
    if (drawer && backdrop) {
      backdrop.classList.remove("hidden");
      drawer.classList.remove("translate-x-full");
    }
  }

  closeDetailDrawer() {
    const drawer = document.getElementById("detail-drawer");
    const backdrop = document.getElementById("drawer-backdrop");
    if (drawer && backdrop) {
      drawer.classList.add("translate-x-full");
      backdrop.classList.add("hidden");
    }
    this.selectedTicker = null;
  }

  renderDrawer(t) {
    const container = document.getElementById("drawer-content");
    if (!container) return;

    const isUpVisit = t.attention.delta_since_visit_pct >= 0;
    const isUpToday = t.change_today_pct >= 0;
    const reasonsHtml = t.attention.reasons
      .map((r) => `<li class="p-2 rounded bg-slate-800/60 border border-white/5 text-xs text-slate-200">✦ ${r}</li>`)
      .join("");

    container.innerHTML = `
      <div class="space-y-6">
        <!-- Header -->
        <div class="flex items-start justify-between">
          <div>
            <div class="flex items-center space-x-3">
              <h2 class="text-2xl font-bold font-mono text-white">${t.symbol}</h2>
              <span class="text-xs px-2.5 py-1 rounded-full badge-${t.attention.tier.toLowerCase()} font-bold">${t.attention.tier}</span>
            </div>
            <p class="text-sm text-slate-400">${t.company_name} • ${t.sector}</p>
          </div>
          <div class="text-right">
            <div class="text-2xl font-bold font-mono text-white">$${t.price.toFixed(2)}</div>
            <div class="text-xs font-mono ${isUpToday ? "text-emerald-400" : "text-rose-400"}">
              ${isUpToday ? "+" : ""}${t.change_today_pct.toFixed(2)}% Today
            </div>
          </div>
        </div>

        <!-- Visit Price Highlight Box -->
        <div class="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-between">
          <div>
            <span class="text-xs uppercase tracking-wider font-semibold text-amber-400">⏱️ Price When You Last Checked</span>
            <div class="text-base font-mono font-bold text-white mt-0.5">
              $${t.attention.price_at_visit ? t.attention.price_at_visit.toFixed(2) : t.previous_close.toFixed(2)}
            </div>
          </div>
          <div class="text-right">
            <span class="text-xs text-slate-400">Delta While Away</span>
            <div class="text-lg font-mono font-bold ${isUpVisit ? "text-emerald-400" : "text-rose-400"}">
              ${isUpVisit ? "+" : ""}${t.attention.delta_since_visit_pct.toFixed(2)}%
            </div>
          </div>
        </div>

        <!-- Interactive Canvas Chart -->
        <div class="glass-panel p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">Price Trend & Visit Benchmark</span>
            <span class="text-[11px] text-amber-400 font-mono">--- Gold Line: Your Visit Price</span>
          </div>
          <canvas id="drawer-chart" width="400" height="200" class="w-full h-48 bg-slate-950/50 rounded-lg"></canvas>
        </div>

        <!-- Quantitative Anomaly Breakdown -->
        <div>
          <h3 class="text-xs uppercase tracking-wider font-bold text-cyan-400 mb-2">Multi-Factor Anomaly Diagnostics</h3>
          <div class="grid grid-cols-2 gap-3">
            <div class="p-3 rounded-lg bg-slate-900/60 border border-white/5">
              <div class="text-[11px] text-slate-400">Statistical Volatility (Z)</div>
              <div class="text-base font-mono font-bold text-white mt-1">${t.attention.z_score.toFixed(2)}σ</div>
              <div class="text-[10px] text-slate-400">Sigma vs normal intraday noise</div>
            </div>
            <div class="p-3 rounded-lg bg-slate-900/60 border border-white/5">
              <div class="text-[11px] text-slate-400">Relative Volume (RVOL)</div>
              <div class="text-base font-mono font-bold text-white mt-1">${t.attention.rvol.toFixed(2)}x</div>
              <div class="text-[10px] text-slate-400">Intraday institutional flow ratio</div>
            </div>
            <div class="p-3 rounded-lg bg-slate-900/60 border border-white/5">
              <div class="text-[11px] text-slate-400">50-Day Moving Average</div>
              <div class="text-base font-mono font-bold text-white mt-1">$${t.sma_50.toFixed(2)}</div>
              <div class="text-[10px] text-slate-400">${t.price >= t.sma_50 ? "Trading Above 50-DMA" : "Breached Below 50-DMA"}</div>
            </div>
            <div class="p-3 rounded-lg bg-slate-900/60 border border-white/5">
              <div class="text-[11px] text-slate-400">52-Week Range</div>
              <div class="text-base font-mono font-bold text-white mt-1">$${t.low_52w.toFixed(0)} - $${t.high_52w.toFixed(0)}</div>
              <div class="text-[10px] text-slate-400">Current: ${( (t.price - t.low_52w) / (t.high_52w - t.low_52w) * 100 ).toFixed(0)}% of range</div>
            </div>
          </div>
        </div>

        <!-- Attention Drivers -->
        <div>
          <h3 class="text-xs uppercase tracking-wider font-bold text-cyan-400 mb-2">Attention Drivers & Signals</h3>
          <ul class="space-y-2">
            ${reasonsHtml}
          </ul>
        </div>

        <!-- Sensitivity & Management Footer -->
        <div class="pt-4 border-t border-white/10 flex items-center justify-between">
          <button onclick="app.removeTickerFromWatchlist('${t.symbol}')"
            class="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 transition">
            Remove from Watchlist
          </button>
          <span class="text-xs font-mono text-slate-400">Feed: ${t.data_health} (${t.latency_ms}ms)</span>
        </div>
      </div>
    `;

    // Draw the chart
    setTimeout(() => {
      const chartCanvas = document.getElementById("drawer-chart");
      if (chartCanvas) {
        window.ChartEngine.drawDetailChart(
          chartCanvas,
          t.historical_bars,
          t.attention.price_at_visit,
          t.price,
          t.sma_50,
          t.sma_200
        );
      }
    }, 50);
  }

  async removeTickerFromWatchlist(symbol) {
    if (!confirm(`Remove ${symbol} from active watchlist?`)) return;

    // Find item ID
    const currentWl = this.watchlists.find((w) => w.id === this.currentWatchlistId);
    if (!currentWl) return;

    const item = currentWl.items.find((i) => i.symbol === symbol);
    if (!item) {
      alert("Item not found in database records.");
      return;
    }

    try {
      const res = await fetch(`/api/watchlists/${this.currentWatchlistId}/items/${item.id}`, {
        method: "DELETE",
      });
      if (res.ok) {
        this.closeDetailDrawer();
        await this.loadWatchlists();
        await this.loadWatchlistAnalysis();
      }
    } catch (err) {
      console.error("Failed to delete item:", err);
    }
  }

  openSearchModal() {
    const modal = document.getElementById("search-modal");
    if (modal) {
      modal.classList.remove("hidden");
      const input = document.getElementById("search-input");
      if (input) {
        input.value = "";
        input.focus();
        this.renderSearchResults([]);
      }
    }
  }

  closeSearchModal() {
    const modal = document.getElementById("search-modal");
    if (modal) modal.classList.add("hidden");
  }

  async handleSearchInput(query) {
    clearTimeout(this.searchDebounce);
    if (!query || query.trim().length === 0) {
      this.renderSearchResults([]);
      return;
    }

    this.searchDebounce = setTimeout(async () => {
      try {
        const res = await fetch(`/api/tickers/search?q=${encodeURIComponent(query.trim())}`);
        if (res.ok) {
          const results = await res.json();
          this.renderSearchResults(results);
        }
      } catch (err) {
        console.error("Search error:", err);
      }
    }, 200);
  }

  renderSearchResults(results) {
    const container = document.getElementById("search-results");
    if (!container) return;

    if (results.length === 0) {
      container.innerHTML = `<p class="text-xs text-slate-400 p-3 text-center">Type a ticker or company name (e.g. NVDA, AAPL, COIN, PLTR)</p>`;
      return;
    }

    container.innerHTML = results
      .map(
        (r) => `
        <div class="flex items-center justify-between p-3 rounded-lg hover:bg-slate-800/60 border border-transparent hover:border-white/10 transition">
          <div>
            <div class="flex items-center space-x-2">
              <span class="font-mono font-bold text-white">${r.symbol}</span>
              <span class="text-xs text-slate-400">${r.name}</span>
            </div>
            <span class="text-[11px] text-cyan-400">${r.sector}</span>
          </div>
          <button onclick="app.addTickerToWatchlist('${r.symbol}')"
            class="px-3 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition">
            + Add
          </button>
        </div>
      `
      )
      .join("");
  }

  async addTickerToWatchlist(symbol) {
    if (!this.currentWatchlistId) return;

    try {
      const res = await fetch(`/api/watchlists/${this.currentWatchlistId}/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: symbol,
          custom_notes: "Added via Smart Search",
          tags: ["Portfolio"],
          custom_sensitivity: "normal",
        }),
      });

      if (res.ok) {
        this.closeSearchModal();
        await this.loadWatchlists();
        await this.loadWatchlistAnalysis();
      } else {
        const err = await res.json();
        alert(err.detail || "Failed to add ticker.");
      }
    } catch (e) {
      console.error("Add item error:", e);
    }
  }

  openNewWatchlistModal() {
    const modal = document.getElementById("new-watchlist-modal");
    if (modal) modal.classList.remove("hidden");
  }

  closeNewWatchlistModal() {
    const modal = document.getElementById("new-watchlist-modal");
    if (modal) modal.classList.add("hidden");
  }

  async createNewWatchlist() {
    const nameInput = document.getElementById("new-wl-name");
    const descInput = document.getElementById("new-wl-desc");
    const symsInput = document.getElementById("new-wl-symbols");

    if (!nameInput || !nameInput.value.trim()) {
      alert("Please provide a watchlist name.");
      return;
    }

    const symbols = symsInput.value
      .split(",")
      .map((s) => s.trim().toUpperCase())
      .filter((s) => s.length > 0);

    try {
      const res = await fetch(`/api/users/${this.currentUserId}/watchlists`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: nameInput.value.trim(),
          description: descInput ? descInput.value.trim() : "",
          symbols: symbols,
        }),
      });

      if (res.ok) {
        const created = await res.json();
        this.currentWatchlistId = created.id;
        this.closeNewWatchlistModal();
        await this.loadWatchlists();
        await this.loadWatchlistAnalysis();
      }
    } catch (err) {
      console.error("Failed to create watchlist:", err);
    }
  }

  showLoading(show) {
    const loader = document.getElementById("loading-spinner");
    if (loader) {
      if (show) loader.classList.remove("hidden");
      else loader.classList.add("hidden");
    }
  }

  bindEvents() {
    // User switch
    const userSelect = document.getElementById("user-select");
    if (userSelect) {
      userSelect.addEventListener("change", async (e) => {
        this.currentUserId = parseInt(e.target.value);
        this.currentWatchlistId = null;
        await this.loadWatchlists();
        await this.timeMachine.loadSnapshots(this.currentUserId);
        await this.loadWatchlistAnalysis();
      });
    }

    // Watchlist switch
    const wlSelect = document.getElementById("watchlist-select");
    if (wlSelect) {
      wlSelect.addEventListener("change", async (e) => {
        this.currentWatchlistId = parseInt(e.target.value);
        await this.loadWatchlistAnalysis();
      });
    }

    // View mode switches
    document.querySelectorAll(".view-mode-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        document.querySelectorAll(".view-mode-btn").forEach((b) => {
          b.classList.remove("bg-cyan-600", "text-white");
          b.classList.add("text-slate-400", "hover:text-white");
        });
        btn.classList.add("bg-cyan-600", "text-white");
        btn.classList.remove("text-slate-400");
        this.activeViewMode = btn.dataset.mode;
        this.renderWatchlist();
      });
    });

    // Time Machine Slider
    const timeSlider = document.getElementById("time-machine-slider");
    const timeValDisplay = document.getElementById("time-slider-val");
    if (timeSlider) {
      timeSlider.addEventListener("input", (e) => {
        const mins = parseInt(e.target.value);
        if (mins < 60) timeValDisplay.textContent = `${mins}m ago`;
        else timeValDisplay.textContent = `${(mins / 60).toFixed(1)}h ago`;
      });
      timeSlider.addEventListener("change", (e) => {
        this.timeMachine.simulateMinutesAgo(parseInt(e.target.value));
      });
    }

    // Snapshot Dropdown
    const snapSelect = document.getElementById("snapshot-select");
    if (snapSelect) {
      snapSelect.addEventListener("change", (e) => {
        this.timeMachine.selectSnapshot(e.target.value);
      });
    }

    // Search input
    const searchInput = document.getElementById("search-input");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        this.handleSearchInput(e.target.value);
      });
    }

    // Keyboard shortcuts
    window.addEventListener("keydown", (e) => {
      if (e.key === "/" && document.activeElement.tagName !== "INPUT") {
        e.preventDefault();
        this.openSearchModal();
      } else if (e.key === "Escape") {
        this.closeSearchModal();
        this.closeDetailDrawer();
        this.closeNewWatchlistModal();
      }
    });
  }
}

window.app = new NexusPulseApp();
window.addEventListener("DOMContentLoaded", () => {
  window.app.init();
});
