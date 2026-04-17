import { drawSparkline } from '../../components/sparkline.js';
import { icon } from '../../components/icons.js';

let rewardHistory = [];
let pollingInterval = null;
let uiInstances = [];
let consecutiveFailures = 0;

/** Shared latest status — consumed by top bar, mini-strip, mobile peek */
export const latestStatus = {
    stage: null,
    episode: null,
    winRate: null,
    winRatePct: null,
    gradStreak: null,
    avgReward: null,
};

async function pollTrainingStatus() {
    if (uiInstances.length === 0) return;
    try {
        const response = await fetch(`/logs/run_latest/training_status.json`, { cache: 'no-store' });
        if (!response.ok) {
            consecutiveFailures++;
            return;
        }
        consecutiveFailures = 0;
        
        const data = await response.json();
        
        // Populate shared status
        if (data.stage !== undefined) latestStatus.stage = data.stage;
        if (data.episode !== undefined) latestStatus.episode = data.episode;
        if (data.win_rate !== undefined) {
            latestStatus.winRate = parseFloat(data.win_rate);
            latestStatus.winRatePct = Math.round(latestStatus.winRate * 100);
        }
        if (data.grad_streak !== undefined) latestStatus.gradStreak = data.grad_streak;

        // Use real reward data from training status if available
        if (data.avg_reward !== undefined) {
            const r = parseFloat(data.avg_reward);
            latestStatus.avgReward = r;
            rewardHistory.push(r);
        } else if (data.recent_reward !== undefined) {
            const r = parseFloat(data.recent_reward);
            latestStatus.avgReward = r;
            rewardHistory.push(r);
        }
        // Cap history length
        if (rewardHistory.length > 50) rewardHistory.shift();
        
        for (const ui of uiInstances) {
            if (data.stage !== undefined) ui.stage.textContent = `Stage ${data.stage}`;
            if (data.episode !== undefined) ui.ep.textContent = data.episode;
            
            if (latestStatus.winRatePct !== null) {
                ui.wr.textContent = latestStatus.winRatePct + '%';
                ui.wrBar.style.width = latestStatus.winRatePct + '%';
            }
            
            if (data.grad_streak !== undefined) {
                ui.streak.textContent = data.grad_streak;
                ui.streak.className = data.grad_streak >= 0 ? "streak-badge dash-streak win" : "streak-badge dash-streak loss";
            }
            
            if (rewardHistory.length > 0) {
                drawSparkline(ui.sparkCanvas, rewardHistory, { strokeColor: '#06d6a0', fillColor: 'rgba(6, 214, 160, 0.15)', showZeroLine: true, showLabels: true });
            }
        }

    } catch (e) {
        consecutiveFailures++;
        // Silently ignore if not running
    }
}

export default {
    id: 'dashboard',
    title: 'Training Dashboard',
    icon: icon('chart-line'),
    modes: ['training'],
    defaultExpanded: true,
    render(body) {
        body.innerHTML = `
            <div class="training-dashboard">
                <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: var(--space-md);">
                    <div class="stage-badge dash-stage">Stage ?</div>
                    <div class="streak-badge dash-streak win" style="padding: 2px 8px; border-radius: var(--radius-full); font-size: var(--font-size-xs); font-weight: 600;">0</div>
                </div>

                <div class="metric-hero dash-ep" style="margin-bottom: var(--space-md); text-align: center; font-size: var(--font-size-hero); color: var(--text-primary); font-family: var(--font-mono);">
                    0
                </div>
                <div style="text-align: center; font-size: var(--font-size-xs); color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: var(--space-md);">
                    Episodes
                </div>

                <div style="margin-bottom: var(--space-md);">
                    <div style="display: flex; justify-content: space-between; margin-bottom: var(--space-xs); font-size: var(--font-size-xs); text-transform: uppercase; color: var(--text-secondary);">
                        <span>Win Rate</span>
                        <span class="dash-wr mono" style="color: var(--text-primary);">0%</span>
                    </div>
                    <div style="position: relative; width: 100%; height: 6px; background: var(--bg-surface-raised); border-radius: 3px; overflow: hidden;">
                        <div class="dash-wr-fill" style="position: absolute; left: 0; top: 0; height: 100%; width: 0%; background: linear-gradient(90deg, var(--accent-danger), var(--accent-warning) 50%, var(--accent-primary)); transition: width 0.3s ease;"></div>
                        <div style="position: absolute; left: 80%; top: 0; bottom: 0; width: 2px; background: rgba(255,255,255,0.7); z-index: 2;" title="80% Graduation Threshold"></div>
                    </div>
                </div>

                <div style="margin-top: var(--space-lg);">
                    <div style="font-size: var(--font-size-xs); color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: var(--space-xs);">Reward History</div>
                    <canvas class="reward-chart canvas-reward-spark" width="300" height="100" style="width: 100%; height: 100px; display: block; border: 1px solid var(--border-subtle); background: var(--bg-surface-raised);"></canvas>
                </div>
            </div>
        `;
        uiInstances.push({
            stage: body.querySelector('.dash-stage'),
            ep: body.querySelector('.dash-ep'),
            wr: body.querySelector('.dash-wr'),
            wrBar: body.querySelector('.dash-wr-fill'),
            streak: body.querySelector('.dash-streak'),
            sparkCanvas: body.querySelector('.canvas-reward-spark')
        });
        
        if (!pollingInterval) {
            // Use adaptive polling: 5s when training data found, 30s after failures
            const poll = () => {
                pollTrainingStatus();
                const nextDelay = consecutiveFailures >= 3 ? 30000 : 5000;
                pollingInterval = setTimeout(poll, nextDelay);
            };
            poll();
        }
    }
};
