export class MotionChart {
  constructor(canvas, capacity = 120) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d");
    this.capacity = capacity;
    this.samples = [];
    this.resizeObserver = new ResizeObserver(() => this.draw());
    this.resizeObserver.observe(canvas);
    this.draw();
  }

  push(values) {
    this.samples.push(values);
    if (this.samples.length > this.capacity) this.samples.shift();
    this.draw();
  }

  draw() {
    const rect = this.canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const ratio = window.devicePixelRatio || 1;
    this.canvas.width = Math.round(rect.width * ratio);
    this.canvas.height = Math.round(rect.height * ratio);
    const ctx = this.context;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    const width = rect.width;
    const height = rect.height;
    const pad = { left: 32, right: 8, top: 10, bottom: 17 };
    const chartWidth = width - pad.left - pad.right;
    const chartHeight = height - pad.top - pad.bottom;
    const range = 250;

    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = "rgba(115,132,113,.13)";
    ctx.lineWidth = 1;
    ctx.fillStyle = "#a1aaa0";
    ctx.font = "9px ui-monospace, monospace";
    for (let step = -2; step <= 2; step += 1) {
      const y = pad.top + ((2 - step) / 4) * chartHeight;
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(width - pad.right, y);
      ctx.stroke();
      ctx.fillText(String(step * 100), 2, y + 3);
    }
    if (this.samples.length < 2) return;

    const series = [
      { index: 0, color: "#6f94d6" },
      { index: 1, color: "#d6a85d" },
      { index: 2, color: "#87ab55" },
    ];
    for (const line of series) {
      ctx.beginPath();
      this.samples.forEach((sample, index) => {
        const x = pad.left + (index / (this.capacity - 1)) * chartWidth;
        const value = Math.max(-range, Math.min(range, sample[line.index]));
        const y = pad.top + ((range - value) / (range * 2)) * chartHeight;
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.strokeStyle = line.color;
      ctx.lineWidth = 1.7;
      ctx.lineJoin = "round";
      ctx.stroke();
    }
  }
}
