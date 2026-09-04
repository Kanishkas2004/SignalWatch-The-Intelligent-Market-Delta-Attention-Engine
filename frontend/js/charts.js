/**
 * Nexus Pulse - High-Performance Canvas Financial Charting Engine
 */

class ChartEngine {
  /**
   * Draws a sleek sparkline on a small canvas element
   */
  static drawSparkline(canvas, dataPoints, isPositive) {
    if (!canvas || !dataPoints || dataPoints.length < 2) return;
    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    const min = Math.min(...dataPoints);
    const max = Math.max(...dataPoints);
    const range = max - min || 1;

    const strokeColor = isPositive ? "#10b981" : "#f43f5e";
    const fillColor = isPositive ? "rgba(16, 185, 129, 0.12)" : "rgba(244, 63, 94, 0.12)";

    ctx.beginPath();
    const step = width / (dataPoints.length - 1);

    dataPoints.forEach((val, idx) => {
      const x = idx * step;
      const y = height - ((val - min) / range) * (height - 6) - 3;
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });

    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 1.8;
    ctx.stroke();

    // Fill area under sparkline
    ctx.lineTo(width, height);
    ctx.lineTo(0, height);
    ctx.closePath();
    ctx.fillStyle = fillColor;
    ctx.fill();
  }

  /**
   * Draws an interactive detailed chart inside the ticker drawer with:
   * - Price history & area fill
   * - Visit reference price annotation line
   * - 50-DMA and 200-DMA guides
   */
  static drawDetailChart(canvas, historicalBars, visitPrice, currentPrice, sma50, sma200) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    // Default synthetic bars if history is empty
    let bars = historicalBars && historicalBars.length > 0 ? historicalBars : [];
    if (bars.length === 0) {
      let p = currentPrice * 0.92;
      for (let i = 25; i >= 0; i--) {
        p = p * (1 + (Math.random() * 0.03 - 0.014));
        bars.push({ close: p, date: `Day -${i}` });
      }
      bars.push({ close: currentPrice, date: "Today" });
    }

    const prices = bars.map(b => b.close || b);
    prices.push(currentPrice);
    if (visitPrice) prices.push(visitPrice);
    if (sma50) prices.push(sma50);

    const minPrice = Math.min(...prices) * 0.985;
    const maxPrice = Math.max(...prices) * 1.015;
    const range = maxPrice - minPrice || 1;

    const getY = (val) => height - ((val - minPrice) / range) * (height - 40) - 20;

    // 1. Draw subtle background horizontal grid lines
    ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
    ctx.lineWidth = 1;
    for (let i = 0; i < 5; i++) {
      const p = minPrice + (range / 4) * i;
      const y = getY(p);
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();

      ctx.fillStyle = "#64748b";
      ctx.font = "10px monospace";
      ctx.fillText(`$${p.toFixed(2)}`, width - 50, y - 4);
    }

    // 2. Draw 50 DMA Guide line if available
    if (sma50) {
      const y50 = getY(sma50);
      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = "rgba(14, 165, 233, 0.5)";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(0, y50);
      ctx.lineTo(width, y50);
      ctx.stroke();
      ctx.fillStyle = "#38bdf8";
      ctx.fillText(`50-DMA: $${sma50.toFixed(2)}`, 10, y50 - 4);
      ctx.setLineDash([]);
    }

    // 3. Draw Visit Price Annotation (Golden Dashed Line)
    if (visitPrice) {
      const yVisit = getY(visitPrice);
      ctx.setLineDash([6, 4]);
      ctx.strokeStyle = "#f59e0b";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(0, yVisit);
      ctx.lineTo(width, yVisit);
      ctx.stroke();

      // Golden Badge
      ctx.fillStyle = "#f59e0b";
      ctx.font = "bold 11px sans-serif";
      ctx.fillText(`📍 Visit Price: $${visitPrice.toFixed(2)}`, width - 150, yVisit - 6);
      ctx.setLineDash([]);
    }

    // 4. Draw Main Price Path & Gradient
    const step = (width - 70) / (bars.length - 1);
    const isUp = currentPrice >= (bars[0].close || bars[0]);

    ctx.beginPath();
    bars.forEach((b, i) => {
      const val = b.close || b;
      const x = i * step + 10;
      const y = getY(val);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });

    const lineColor = isUp ? "#10b981" : "#f43f5e";
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Gradient fill
    const grad = ctx.createLinearGradient(0, 0, 0, height);
    grad.addColorStop(0, isUp ? "rgba(16, 185, 129, 0.25)" : "rgba(244, 63, 94, 0.25)");
    grad.addColorStop(1, "rgba(0, 0, 0, 0)");
    ctx.lineTo(width - 60, height);
    ctx.lineTo(10, height);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Pulse dot at latest price
    const latestX = (bars.length - 1) * step + 10;
    const latestY = getY(currentPrice);
    ctx.beginPath();
    ctx.arc(latestX, latestY, 5, 0, Math.PI * 2);
    ctx.fillStyle = lineColor;
    ctx.fill();
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
}

window.ChartEngine = ChartEngine;
