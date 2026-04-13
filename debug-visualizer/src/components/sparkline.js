// ─── Reusable Sparkline Chart ──────────────────────────────────

/**
 * Draw a sparkline on a canvas element.
 * @param {HTMLCanvasElement} canvas
 * @param {number[]} values
 * @param {Object} [opts]
 * @param {string} [opts.strokeColor='#06d6a0']
 * @param {string} [opts.fillColor='rgba(6, 214, 160, 0.15)']
 * @param {number} [opts.lineWidth=2]
 * @param {boolean} [opts.showZeroLine=true]
 */
export function drawSparkline(canvas, values, opts = {}) {
  if (!values || values.length === 0) return;
  const ctx = canvas.getContext('2d');
  const { width, height } = canvas;
  const strokeColor = opts.strokeColor || '#06d6a0';
  const fillColor = opts.fillColor || 'rgba(6, 214, 160, 0.15)';
  const lineWidth = opts.lineWidth || 2;
  const showZeroLine = opts.showZeroLine ?? true;
  
  ctx.clearRect(0, 0, width, height);
  
  const padding = 2;
  const drawW = width - padding * 2;
  const drawH = height - padding * 2;
  
  const maxVal = Math.max(...values, 0.001);
  const minVal = Math.min(...values, 0);
  const range = maxVal - minVal || 1;
  const step = drawW / Math.max(values.length - 1, 1);
  
  // Line
  ctx.beginPath();
  values.forEach((v, i) => {
    const x = padding + i * step;
    const y = padding + drawH - ((v - minVal) / range) * drawH;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = lineWidth;
  ctx.lineJoin = 'round';
  ctx.stroke();
  
  // Fill
  ctx.lineTo(padding + (values.length - 1) * step, padding + drawH);
  ctx.lineTo(padding, padding + drawH);
  ctx.closePath();
  ctx.fillStyle = fillColor;
  ctx.fill();
  
  // Zero line
  if (showZeroLine && minVal < 0 && maxVal > 0) {
    const zeroY = padding + drawH - ((0 - minVal) / range) * drawH;
    ctx.beginPath();
    ctx.moveTo(padding, zeroY);
    ctx.lineTo(padding + drawW, zeroY);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.stroke();
    ctx.setLineDash([]);
  }
}
