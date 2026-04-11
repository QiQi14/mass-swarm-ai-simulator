const POLL_INTERVAL_MS = 5000;
const CSV_URL = '/logs/run_latest/episode_log.csv';
const TAIL_BYTES = 4096;

let overlayVisible = false;
let pollTimer = null;
let cachedEpisodeCount = 0;

export function initTrainingOverlay() {
    createOverlayDOM();
    startPolling();
    document.addEventListener('keydown', (e) => {
        if (e.key === 't' || e.key === 'T') toggleOverlay();
    });
}

function toggleOverlay() {
    overlayVisible = !overlayVisible;
    const overlay = document.getElementById('training-overlay');
    if (overlayVisible) {
        overlay.classList.remove('hidden');
    } else {
        overlay.classList.add('hidden');
    }
}

function createOverlayDOM() {
    const overlay = document.createElement('div');
    overlay.id = 'training-overlay';
    // Hidden by default, press T to show, but instructions say "Toggle-able via T key", so maybe it should be visible initially? Or hidden initially? Unclear. Let's make it hidden initially and let user press T. Or wait, "Overlay panel appears when pressing 'T' key", imply hidden by default.
    overlay.classList.add('hidden');

    overlay.innerHTML = `
        <div class="training-header">
            <h3>Training Overlay</h3>
            <button class="toggle-overlay-btn" id="training-overlay-close">&times;</button>
        </div>
        <div id="training-content" style="display: none;">
            <div class="training-metric">
                <span class="label">Episodes</span>
                <span class="value" id="training-episodes">0</span>
            </div>
            <div class="training-metric">
                <span class="label">Stage</span>
                <span class="value" id="training-stage">0</span>
            </div>
            <div class="winrate-container">
                <div class="winrate-header">
                    <span>Rolling Win Rate</span>
                    <span class="value" id="training-winrate-pct">0%</span>
                </div>
                <div class="winrate-bar">
                    <div class="winrate-bar-fill" id="training-winrate-bar" style="width: 0%; background-color: rgb(255, 100, 100);"></div>
                </div>
            </div>
            <div class="sparkline-container">
                <div class="sparkline-label">Last 20 Rewards</div>
                <canvas id="training-sparkline" width="280" height="60"></canvas>
            </div>
        </div>
        <div class="training-status" id="training-status">Waiting for data...</div>
    `;

    document.body.appendChild(overlay);

    document.getElementById('training-overlay-close').addEventListener('click', toggleOverlay);
}

function startPolling() {
    fetchAndUpdate();
    pollTimer = setInterval(fetchAndUpdate, POLL_INTERVAL_MS);
}

function showStatus(msg) {
    document.getElementById('training-status').style.display = 'block';
    document.getElementById('training-status').innerText = msg;
    document.getElementById('training-content').style.display = 'none';
}

function hideStatus() {
    document.getElementById('training-status').style.display = 'none';
    document.getElementById('training-content').style.display = 'block';
}

async function fetchAndUpdate() {
    if (!overlayVisible) return; // Optional optimization, but maybe we should still fetch? Let's keep fetching so it's fresh when opened. Wait, I will always fetch.
    
    try {
        const resp = await fetch(CSV_URL, {
            headers: { 'Range': `bytes=-${TAIL_BYTES}` }
        });
        if (!resp.ok && resp.status !== 206) {
            showStatus('No active training run');
            return;
        }
        const text = await resp.text();
        const isPartial = resp.status === 206;
        const records = parseCSVTail(text, isPartial);
        if (records.length > 0) {
            updateMetrics(records);
            hideStatus();
        } else {
            showStatus('Parsing data...');
        }
    } catch (e) {
        showStatus('Training data unavailable');
    }
}

function parseCSVTail(text, isPartial) {
    const lines = text.trim().split('\n');
    const startIdx = isPartial ? 1 : 1; // Skip header or truncated line
    const records = [];
    
    for (let i = startIdx; i < lines.length; i++) {
        const parts = lines[i].split(',');
        if (parts.length >= 8) {
            // episode,stage,steps,win,reward,brain_survivors,enemy_survivors,win_rate_rolling
            records.push({
                episode: parseInt(parts[0], 10),
                stage: parseInt(parts[1], 10),
                steps: parseInt(parts[2], 10),
                win: parts[3] === 'True' || parts[3] === '1',
                reward: parseFloat(parts[4]),
                winRate: parseFloat(parts[7])
            });
        }
    }
    return records;
}

function updateMetrics(records) {
    if (records.length === 0) return;
    const latest = records[records.length - 1];
    
    const epElem = document.getElementById('training-episodes');
    const stageElem = document.getElementById('training-stage');
    if (epElem) epElem.innerText = latest.episode;
    if (stageElem) stageElem.innerText = latest.stage;

    const wrBar = document.getElementById('training-winrate-bar');
    const wrPct = document.getElementById('training-winrate-pct');
    if (wrBar && wrPct) {
        const wr = latest.winRate * 100;
        wrPct.innerText = wr.toFixed(1) + '%';
        wrBar.style.width = Math.min(Math.max(wr, 0), 100) + '%';
        
        let color = '#ff4444'; // red
        if (wr > 70) color = '#44ff44'; // green
        else if (wr >= 40) color = '#ffff44'; // yellow
        
        wrBar.style.backgroundColor = color;
    }
    
    const canvas = document.getElementById('training-sparkline');
    if (canvas) {
        const last20 = records.slice(-20).map(r => r.reward);
        drawSparkline(canvas, last20);
    }
}

function drawSparkline(canvas, values) {
    if (values.length === 0) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    ctx.clearRect(0, 0, width, height);
    
    const maxVal = Math.max(...values, 0.001); // avoid 0 div
    const minVal = Math.min(...values, 0);
    const range = maxVal - minVal;
    
    const step = width / Math.max(values.length - 1, 1);
    
    ctx.beginPath();
    for (let i = 0; i < values.length; i++) {
        const x = i * step;
        const normalized = (values[i] - minVal) / range;
        const y = height - (normalized * height);
        
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    
    ctx.strokeStyle = '#64b4ff';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // Fill under the line
    ctx.lineTo(width, height);
    ctx.lineTo(0, height);
    ctx.closePath();
    ctx.fillStyle = 'rgba(100, 180, 255, 0.2)';
    ctx.fill();
    
    // Draw 0 line if it's within range
    if (minVal < 0 && maxVal > 0) {
        const zeroY = height - ((0 - minVal) / range * height);
        ctx.beginPath();
        ctx.moveTo(0, zeroY);
        ctx.lineTo(width, zeroY);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
    }
}
