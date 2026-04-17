import { icon } from '../components/icons.js';

const PRESETS = [
    { key: 'swarm_vs_defender', iconName: 'swords', title: 'Swarm vs Defender', desc: '500 vs 100' },
    { key: 'three_faction_melee', iconName: 'triangle', title: '3-Faction Melee', desc: '3×100 FFA' },
    { key: 'ranged_vs_melee', iconName: 'crosshair', title: 'Ranged vs Melee', desc: '200 vs 200' },
    { key: 'tank_screen', iconName: 'shield', title: 'Tank Screen', desc: '300+100+200' },
    { key: 'waypoint_navigation', iconName: 'mapPin', title: 'Waypoint Rally', desc: '500 → (800,800)' },
    { key: 'blank', iconName: 'plus', title: 'Blank Canvas', desc: 'Start from scratch' }
];

/**
 * Show the preset selection splash overlay.
 * @param {Object} callbacks
 * @param {(presetKey: string) => void} callbacks.onSelect — Called when user picks a preset
 * @param {() => void} callbacks.onBlank — Called when user chooses "Create from Scratch"
 */
export function showPresetGallery({ onSelect, onBlank }) {
    if (document.getElementById('preset-gallery')) {
        return;
    }

    // Disable drawflow pointer events so it doesn't intercept clicks
    const drawflowEl = document.getElementById('drawflow-container');
    if (drawflowEl) drawflowEl.style.pointerEvents = 'none';

    const container = document.createElement('div');
    container.className = 'preset-gallery';
    container.id = 'preset-gallery';

    container.innerHTML = `
        <div class="preset-gallery__backdrop"></div>
        <div class="preset-gallery__dialog">
            <h2 class="preset-gallery__title">SELECT A SCENARIO</h2>
            <div class="preset-gallery__grid">
                ${PRESETS.map(p => `
                <button class="preset-card" data-preset="${p.key}">
                    <div class="preset-card__icon">${icon(p.iconName, 32)}</div>
                    <div class="preset-card__title">${p.title}</div>
                    <div class="preset-card__desc">${p.desc}</div>
                </button>
                `).join('')}
            </div>
            <div class="preset-gallery__footer">
                <button class="preset-gallery__blank-btn">Create from Scratch</button>
            </div>
        </div>
    `;

    document.body.appendChild(container);

    // Wrap callbacks to always restore drawflow pointer events
    const wrapClose = (fn) => () => {
        if (drawflowEl) drawflowEl.style.pointerEvents = '';
        fn();
    };

    // Event listeners
    const buttons = container.querySelectorAll('.preset-card');
    buttons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const presetKey = btn.getAttribute('data-preset');
            if (presetKey === 'blank') {
                wrapClose(onBlank)();
            } else {
                wrapClose(() => onSelect(presetKey))();
            }
        });
    });

    const blankBtn = container.querySelector('.preset-gallery__blank-btn');
    blankBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        wrapClose(onBlank)();
    });

    const backdrop = container.querySelector('.preset-gallery__backdrop');
    backdrop.addEventListener('click', () => {
        wrapClose(onBlank)();
    });

    // Force reflow for animation
    void container.offsetWidth;
    container.classList.add('preset-gallery--open');
}

/**
 * Hide and remove the splash overlay from DOM.
 */
export function hidePresetGallery() {
    const container = document.getElementById('preset-gallery');
    if (container) {
        container.classList.remove('preset-gallery--open');
        // Use timeout fallback — transitionend can be unreliable
        const cleanup = () => {
            if (container.parentNode) container.remove();
        };
        container.addEventListener('transitionend', cleanup, { once: true });
        setTimeout(cleanup, 350); // Fallback
    }

    // Restore drawflow pointer events
    const drawflowEl = document.getElementById('drawflow-container');
    if (drawflowEl) drawflowEl.style.pointerEvents = '';
}
