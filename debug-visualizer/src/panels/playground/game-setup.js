import * as S from '../../state.js';
import { sendCommand } from '../../websocket.js';
import { applyPreset, getPresetKeys, getPreset, sendNavRule, sendInteractionRule, sendRemovalRule } from '../../controls/algorithm-test.js';

export default {
    id: 'game-setup',
    title: 'Game Setup',
    icon: '🚀',
    modes: ['playground'],
    defaultExpanded: true,
    render(body) {
        body.innerHTML = `
            <div class="game-setup-tabs">
                <button class="game-setup-tab active" id="game-setup-tab-presets">Presets</button>
                <button class="game-setup-tab" id="game-setup-tab-custom">Custom</button>
            </div>
            
            <div id="game-setup-view-presets" class="game-setup-view">
                <div class="stat-grid" id="game-setup-presets-grid" style="grid-template-columns: 1fr 1fr; margin-bottom: var(--space-md);">
                    <!-- Populated by JS -->
                </div>
            </div>

            <div id="game-setup-view-custom" class="game-setup-view" style="display: none;">
                <div class="wizard-steps" style="display: flex; gap: var(--space-sm); margin-bottom: var(--space-md); color: var(--text-tertiary); font-size: var(--font-size-xs); align-items: center;">
                    <div id="wizard-step-1" class="wizard-step active" style="color: var(--text-primary);">1. Factions</div>
                    <div>&mdash;</div>
                    <div id="wizard-step-2" class="wizard-step">2. Rules</div>
                    <div>&mdash;</div>
                    <div id="wizard-step-3" class="wizard-step">3. Launch</div>
                </div>

                <!-- Step 1: Factions -->
                <div id="wizard-content-1" class="wizard-content">
                    <div id="wizard-factions-list" style="display: flex; flex-direction: column; gap: var(--space-sm); margin-bottom: var(--space-md);">
                        <!-- Cards populated dynamically -->
                    </div>
                    <button class="btn accent outline" id="wizard-add-faction-btn" style="width: 100%; margin-bottom: var(--space-md);">+ Add Faction</button>
                    <div style="display: flex; justify-content: flex-end;">
                        <button class="btn primary" id="wizard-next-1">Next ▸</button>
                    </div>
                </div>

                <!-- Step 2: Rules -->
                <div id="wizard-content-2" class="wizard-content" style="display: none;">
                    <div class="stat-card" style="padding: var(--space-md); margin-bottom: var(--space-md);">
                        <div class="stat-label" style="margin-bottom: var(--space-sm);">Who fights whom?</div>
                        <div id="wizard-combat-matrix" style="display: grid; gap: var(--space-xs);">
                            <!-- Populated dynamically -->
                        </div>
                    </div>
                    <div class="stat-card" style="padding: var(--space-md); margin-bottom: var(--space-md);">
                        <div class="stat-label" style="margin-bottom: var(--space-sm);">Lethality</div>
                        <select id="wizard-damage-select" class="input" style="width: 100%; margin-bottom: var(--space-sm);">
                            <option value="-0.5">Light Damage (-0.5)</option>
                            <option value="-1.0" selected>Normal Damage (-1.0)</option>
                            <option value="-2.0">Heavy Damage (-2.0)</option>
                        </select>
                        <div class="stat-label" style="margin-bottom: var(--space-sm);">Range</div>
                        <select id="wizard-range-select" class="input" style="width: 100%;">
                            <option value="15.0">Close (15m)</option>
                            <option value="30.0" selected>Mid (30m)</option>
                            <option value="60.0">Far (60m)</option>
                        </select>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <button class="btn outline" id="wizard-prev-2">◂ Back</button>
                        <button class="btn primary" id="wizard-next-2">Next ▸</button>
                    </div>
                </div>

                <!-- Step 3: Launch -->
                <div id="wizard-content-3" class="wizard-content" style="display: none;">
                    <div class="stat-card" style="padding: var(--space-md); margin-bottom: var(--space-md);">
                        <div class="stat-label" style="margin-bottom: var(--space-sm);">Map Size</div>
                        <div style="display: flex; gap: var(--space-sm);">
                            <button class="btn outline map-size-btn" data-size="400">Small</button>
                            <button class="btn primary map-size-btn" data-size="600" style="flex: 1;">Medium</button>
                            <button class="btn outline map-size-btn" data-size="1000">Large</button>
                        </div>
                    </div>
                    <button class="btn primary launch" id="wizard-launch-btn" style="width: 100%; padding: var(--space-md); font-size: var(--font-size-lg); background: var(--accent-primary); color: #000;">🚀 Start Simulation</button>
                    <div style="display: flex; justify-content: flex-start; margin-top: var(--space-md);">
                        <button class="btn outline" id="wizard-prev-3">◂ Back</button>
                    </div>
                </div>
            </div>

            <!-- Advanced Controls Toggle -->
            <div class="advanced-toggle" style="margin-top: var(--space-md); border-top: 1px solid var(--border-subtle); padding-top: var(--space-sm);">
                <button id="game-setup-advanced-btn" style="background: none; border: none; color: var(--text-tertiary); font-size: var(--font-size-xs); cursor: pointer; display: flex; align-items: center; gap: var(--space-xs);">
                    ⚙ Advanced Controls <span id="game-setup-advanced-chevron">▸</span>
                </button>
                <div id="game-setup-advanced-content" style="display: none; margin-top: var(--space-sm);">
                    <!-- Nav Rules -->
                    <div class="stat-card" style="padding: var(--space-sm); margin-bottom: var(--space-sm);">
                        <div class="stat-label">Navigation Rule</div>
                        <div style="display: flex; gap: var(--space-sm); margin-top: var(--space-xs);">
                            <input type="number" id="adv-nav-follower" class="input" placeholder="Faction" style="width: 60px;">
                            <select id="adv-nav-type" class="input">
                                <option value="Faction">Target Faction</option>
                                <option value="Waypoint">Waypoint (x,y)</option>
                            </select>
                            <input type="text" id="adv-nav-target" class="input" placeholder="0 or x,y" style="width: 80px;">
                            <button class="btn primary" id="adv-nav-btn">Set</button>
                        </div>
                    </div>
                    <!-- Interaction Rules -->
                    <div class="stat-card" style="padding: var(--space-sm); margin-bottom: var(--space-sm);">
                        <div class="stat-label">Interaction Rule</div>
                         <div style="display: flex; gap: var(--space-sm); margin-top: var(--space-xs); flex-wrap: wrap;">
                            <input type="number" id="adv-int-source" class="input" placeholder="Src" style="width: 50px;">
                            <input type="number" id="adv-int-target" class="input" placeholder="Tgt" style="width: 50px;">
                            <input type="number" id="adv-int-range" class="input" placeholder="Range" style="width: 60px;" value="15.0">
                            <input type="number" id="adv-int-stat" class="input" placeholder="Stat" style="width: 50px;" value="0">
                            <input type="number" id="adv-int-delta" class="input" placeholder="Delta/s" style="width: 60px;" value="-10.0">
                            <button class="btn primary" id="adv-int-btn">Set</button>
                        </div>
                    </div>
                    <!-- Removal Rules -->
                    <div class="stat-card" style="padding: var(--space-sm);">
                        <div class="stat-label">Removal Rule</div>
                         <div style="display: flex; gap: var(--space-sm); margin-top: var(--space-xs);">
                            <input type="number" id="adv-rem-stat" class="input" placeholder="Stat" style="width: 60px;" value="0">
                            <select id="adv-rem-cond" class="input">
                                <option value="LessThanEqual">≤</option>
                                <option value="GreaterThanEqual">≥</option>
                                <option value="Equal">=</option>
                            </select>
                            <input type="number" id="adv-rem-thresh" class="input" placeholder="Thresh" style="width: 60px;" value="0.0">
                            <button class="btn primary" id="adv-rem-btn">Set</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // ── Tabs Logic ──
        const tabPresets = body.querySelector('#game-setup-tab-presets');
        const tabCustom = body.querySelector('#game-setup-tab-custom');
        const viewPresets = body.querySelector('#game-setup-view-presets');
        const viewCustom = body.querySelector('#game-setup-view-custom');

        tabPresets.onclick = () => {
            tabPresets.classList.add('active');
            tabCustom.classList.remove('active');
            viewPresets.style.display = 'block';
            viewCustom.style.display = 'none';
        };
        tabCustom.onclick = () => {
            tabCustom.classList.add('active');
            tabPresets.classList.remove('active');
            viewCustom.style.display = 'block';
            viewPresets.style.display = 'none';
        };

        // ── Presets Population ──
        const presetsGrid = body.querySelector('#game-setup-presets-grid');
        getPresetKeys().forEach(key => {
            const preset = getPreset(key);
            const card = document.createElement('div');
            card.className = 'stat-card';
            card.style.padding = 'var(--space-sm)';
            card.style.cursor = 'pointer';
            card.innerHTML = `
                <div style="font-weight: bold; color: var(--text-primary); margin-bottom: 4px;">${preset.label}</div>
                <div style="font-size: var(--font-size-2xs); color: var(--text-secondary);">${preset.description}</div>
            `;
            card.onclick = () => applyPreset(key);
            presetsGrid.appendChild(card);
        });

        // ── Custom Wizard Logic ──
        const contents = [
            body.querySelector('#wizard-content-1'),
            body.querySelector('#wizard-content-2'),
            body.querySelector('#wizard-content-3')
        ];
        const stepIndicators = [
            body.querySelector('#wizard-step-1'),
            body.querySelector('#wizard-step-2'),
            body.querySelector('#wizard-step-3')
        ];

        let currentStep = 1;
        const setStep = (step) => {
            if (step < 1 || step > 3) return;
            currentStep = step;
            contents.forEach((c, i) => c.style.display = i + 1 === step ? 'block' : 'none');
            stepIndicators.forEach((ind, i) => {
                if (i + 1 === step) {
                    ind.classList.add('active');
                    ind.style.color = 'var(--text-primary)';
                } else {
                    ind.classList.remove('active');
                    ind.style.color = 'var(--text-tertiary)';
                }
            });
            if (step === 2) buildCombatMatrix();
        };

        body.querySelector('#wizard-next-1').onclick = () => setStep(2);
        body.querySelector('#wizard-prev-2').onclick = () => setStep(1);
        body.querySelector('#wizard-next-2').onclick = () => setStep(3);
        body.querySelector('#wizard-prev-3').onclick = () => setStep(2);

        // Map size selection
        let selectedMapSize = 600;
        const mapButtons = body.querySelectorAll('.map-size-btn');
        mapButtons.forEach(btn => {
            btn.onclick = () => {
                mapButtons.forEach(b => { b.classList.remove('primary'); b.classList.add('outline'); });
                btn.classList.add('primary');
                btn.classList.remove('outline');
                selectedMapSize = parseInt(btn.dataset.size);
            };
        });

        // Custom Faction State
        let factions = [
            { id: 0, count: 200, color: 'var(--color-swarm)' },
            { id: 1, count: 200, color: 'var(--color-defender)' }
        ];

        const factionsList = body.querySelector('#wizard-factions-list');
        const renderFactions = () => {
            factionsList.innerHTML = '';
            factions.forEach((fc, idx) => {
                const fCard = document.createElement('div');
                fCard.className = 'stat-card';
                fCard.style.padding = 'var(--space-sm)';
                fCard.style.display = 'flex';
                fCard.style.alignItems = 'center';
                fCard.style.gap = 'var(--space-sm)';
                fCard.innerHTML = `
                    <div style="width: 16px; height: 16px; border-radius: 50%; background: ${fc.color}; box-shadow: 0 0 8px ${fc.color};"></div>
                    <div style="flex: 1;">Faction ${fc.id}</div>
                    <input type="range" class="input" min="10" max="1000" step="10" value="${fc.count}" style="width: 80px;">
                    <span style="font-family: var(--font-mono); font-size: var(--font-size-xs); color: var(--text-data); width: 30px; text-align: right;">${fc.count}</span>
                    ${idx > 1 ? '<button class="btn error" style="padding: 2px 6px;">×</button>' : ''}
                `;

                const countSlider = fCard.querySelector('input[type="range"]');
                const countText = fCard.querySelector('span');
                countSlider.oninput = (e) => {
                    fc.count = parseInt(e.target.value);
                    countText.textContent = fc.count;
                };

                if (idx > 1) {
                    fCard.querySelector('button.error').onclick = () => {
                        factions = factions.filter(f => f.id !== fc.id);
                        renderFactions();
                    };
                }
                factionsList.appendChild(fCard);
            });
            body.querySelector('#wizard-add-faction-btn').style.display = factions.length < 4 ? 'block' : 'none';
        };

        body.querySelector('#wizard-add-faction-btn').onclick = () => {
             if (factions.length >= 4) return;
             const nextId = factions.length > 0 ? Math.max(...factions.map(f => f.id)) + 1 : 0;
             const newColor = factions.length === 2 ? 'var(--accent-warning)' : 'var(--accent-secondary)';
             factions.push({ id: nextId, count: 200, color: newColor });
             renderFactions();
        };

        renderFactions();

        // Combat Matrix State
        const matrixContainer = body.querySelector('#wizard-combat-matrix');
        const combatChecks = new Map(); // "source-target" -> boolean
        const buildCombatMatrix = () => {
            matrixContainer.innerHTML = '';
            matrixContainer.style.gridTemplateColumns = `auto ${factions.map(() => '1fr').join(' ')}`;
            
            // Header row
            matrixContainer.appendChild(document.createElement('div')); // Empty top left
            factions.forEach(f => {
                const h = document.createElement('div');
                h.style.textAlign = 'center';
                h.style.fontSize = 'var(--font-size-2xs)';
                h.style.color = 'var(--text-secondary)';
                h.textContent = `Tgt ${f.id}`;
                matrixContainer.appendChild(h);
            });

            // Rows
            factions.forEach(src => {
                const rLabel = document.createElement('div');
                rLabel.style.fontSize = 'var(--font-size-2xs)';
                rLabel.style.color = 'var(--text-secondary)';
                rLabel.style.display = 'flex';
                rLabel.style.alignItems = 'center';
                rLabel.textContent = `Src ${src.id}`;
                matrixContainer.appendChild(rLabel);

                factions.forEach(tgt => {
                    const cell = document.createElement('div');
                    cell.style.display = 'flex';
                    cell.style.justifyContent = 'center';
                    if (src.id === tgt.id) {
                        cell.innerHTML = `<span style="color: var(--text-tertiary); font-size: var(--font-size-xs);">-</span>`;
                    } else {
                        const cb = document.createElement('input');
                        cb.type = 'checkbox';
                        const key = `${src.id}-${tgt.id}`;
                        if (!combatChecks.has(key)) cb.checked = true; // default all checked
                        else cb.checked = combatChecks.get(key);
                        cb.onchange = () => combatChecks.set(key, cb.checked);
                        if (!combatChecks.has(key)) combatChecks.set(key, true);
                        cell.appendChild(cb);
                    }
                    matrixContainer.appendChild(cell);
                });
            });
        };

        // Launch logic
        body.querySelector('#wizard-launch-btn').onclick = () => {
            // 1. Kill
            factions.forEach(f => sendCommand('kill_all', { faction_id: f.id }));
            
            // 2. Set Rules
            const dmg = parseFloat(body.querySelector('#wizard-damage-select').value);
            const range = parseFloat(body.querySelector('#wizard-range-select').value);
            const intRules = [];
            const navRules = [];
            
            combatChecks.forEach((isChecked, key) => {
                if (isChecked) {
                    const [sId, tId] = key.split('-').map(Number);
                    intRules.push({
                        source_faction: sId,
                        target_faction: tId,
                        range: range,
                        effects: [{ stat_index: 0, delta_per_second: dmg }]
                    });
                    navRules.push({
                        follower_faction: sId,
                        target: { type: 'Faction', faction_id: tId }
                    });
                }
            });

            const remRules = [{ stat_index: 0, threshold: 0.0, condition: 'LessThanEqual' }];

            sendCommand('set_interaction', { rules: intRules });
            sendCommand('set_navigation', { rules: navRules });
            sendCommand('set_removal', { rules: remRules });

            // 3. Spawn
            setTimeout(() => {
                factions.forEach((f, idx) => {
                    // Spread spawns across the map width based on index
                    const numFactions = factions.length;
                    const xPositions = [selectedMapSize * 0.25, selectedMapSize * 0.75, selectedMapSize * 0.5, selectedMapSize * 0.5];
                    const yPositions = [selectedMapSize * 0.5, selectedMapSize * 0.5, selectedMapSize * 0.25, selectedMapSize * 0.75];
                    const x = xPositions[idx % 4];
                    const y = yPositions[idx % 4];

                    sendCommand('spawn_wave', {
                        faction_id: f.id,
                        amount: f.count,
                        x: x,
                        y: y,
                        spread: Math.max(50, selectedMapSize * 0.1),
                        stats: [{ index: 0, value: 100.0 }]
                    });
                });
            }, 100);
        };

        // ── Advanced Toggle ──
        const advBtn = body.querySelector('#game-setup-advanced-btn');
        const advContent = body.querySelector('#game-setup-advanced-content');
        const advChevron = body.querySelector('#game-setup-advanced-chevron');
        advBtn.onclick = () => {
            const isVis = advContent.style.display === 'block';
            advContent.style.display = isVis ? 'none' : 'block';
            advChevron.textContent = isVis ? '▸' : '▾';
        };

        // Advanced setters
        body.querySelector('#adv-nav-btn').onclick = () => {
            sendNavRule(
                body.querySelector('#adv-nav-follower').value,
                body.querySelector('#adv-nav-type').value,
                body.querySelector('#adv-nav-target').value
            );
        };
        body.querySelector('#adv-int-btn').onclick = () => {
            sendInteractionRule(
                body.querySelector('#adv-int-source').value,
                body.querySelector('#adv-int-target').value,
                body.querySelector('#adv-int-range').value,
                body.querySelector('#adv-int-stat').value,
                body.querySelector('#adv-int-delta').value
            );
        };
        body.querySelector('#adv-rem-btn').onclick = () => {
            sendRemovalRule(
                body.querySelector('#adv-rem-stat').value,
                body.querySelector('#adv-rem-thresh').value,
                body.querySelector('#adv-rem-cond').value
            );
        };
    }
};
