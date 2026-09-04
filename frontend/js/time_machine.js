/**
 * Nexus Pulse - Time Machine & Visit Simulation Controller
 */

class TimeMachineController {
  constructor(app) {
    this.app = app;
    this.activeMinutesAgo = 135; // Default 2h 15m
    this.snapshots = [];
    this.activeSnapshotId = null;
  }

  async loadSnapshots(userId) {
    try {
      const res = await fetch(`/api/users/${userId}/snapshots`);
      if (res.ok) {
        this.snapshots = await res.json();
        this.renderSnapshotSelector();
      }
    } catch (err) {
      console.error("Failed to load visit snapshots:", err);
    }
  }

  renderSnapshotSelector() {
    const select = document.getElementById("snapshot-select");
    if (!select) return;

    select.innerHTML = "";
    this.snapshots.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.label;
      if (this.activeSnapshotId === s.id) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });
  }

  async selectSnapshot(snapshotId) {
    this.activeSnapshotId = parseInt(snapshotId);
    await this.app.loadWatchlistAnalysis();
  }

  async simulateMinutesAgo(minutes) {
    this.activeMinutesAgo = minutes;
    const userId = this.app.currentUserId;

    try {
      const res = await fetch(`/api/users/${userId}/snapshots/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ simulated_minutes_ago: minutes }),
      });

      if (res.ok) {
        const newSnap = await res.json();
        this.activeSnapshotId = newSnap.id;
        // Reload list and re-run analysis
        await this.loadSnapshots(userId);
        await this.app.loadWatchlistAnalysis();
        this.updateTimeMachineStatus(newSnap.label);
      }
    } catch (err) {
      console.error("Simulation error:", err);
    }
  }

  async recordNow() {
    const userId = this.app.currentUserId;
    try {
      const res = await fetch(`/api/users/${userId}/snapshots/record`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (res.ok) {
        const snap = await res.json();
        this.activeSnapshotId = snap.id;
        await this.loadSnapshots(userId);
        await this.app.loadWatchlistAnalysis();
        this.updateTimeMachineStatus("Session bookmarked to Current Time");
      }
    } catch (err) {
      console.error("Error bookmarking session:", err);
    }
  }

  updateTimeMachineStatus(label) {
    const el = document.getElementById("simulation-indicator");
    if (el) {
      el.innerHTML = `<span class="inline-block w-2 h-2 rounded-full bg-amber-400 mr-2 animate-pulse"></span>${label}`;
    }
  }
}

window.TimeMachineController = TimeMachineController;
