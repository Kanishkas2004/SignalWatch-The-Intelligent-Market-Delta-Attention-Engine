/**
 * Nexus Pulse - WebSocket Live Stream Manager
 */
class LiveFeedManager {
  constructor() {
    this.ws = null;
    this.listeners = [];
    this.statusListeners = [];
    this.reconnectAttempts = 0;
    this.maxReconnectDelay = 10000;
    this.pingInterval = null;
    this.isConnected = false;
  }

  connect() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/live`;

    this.updateStatus("CONNECTING");

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.updateStatus("LIVE");
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "TICK_UPDATE") {
            this.broadcastTicks(data.ticks);
          }
        } catch (err) {
          console.error("WS Parse error:", err);
        }
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        this.stopHeartbeat();
        this.updateStatus("DISCONNECTED");
        this.scheduleReconnect();
      };

      this.ws.onerror = (err) => {
        console.warn("WS Error:", err);
        this.ws.close();
      };
    } catch (e) {
      console.error("Failed to initialize WebSocket:", e);
      this.scheduleReconnect();
    }
  }

  startHeartbeat() {
    this.stopHeartbeat();
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ action: "PING" }));
      }
    }, 15000);
  }

  stopHeartbeat() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  scheduleReconnect() {
    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), this.maxReconnectDelay);
    this.reconnectAttempts++;
    setTimeout(() => {
      if (!this.isConnected) {
        this.connect();
      }
    }, delay);
  }

  updateStatus(status) {
    this.statusListeners.forEach((fn) => fn(status));
  }

  onTicks(callback) {
    this.listeners.push(callback);
  }

  onStatusChange(callback) {
    this.statusListeners.push(callback);
  }

  broadcastTicks(ticks) {
    this.listeners.forEach((fn) => fn(ticks));
  }
}

window.liveFeed = new LiveFeedManager();
