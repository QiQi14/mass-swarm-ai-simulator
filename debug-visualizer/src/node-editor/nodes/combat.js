import { registerNodeType } from '../drawflow-setup.js';

const swordsSVG = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 17.5L3 6V3h3l11.5 11.5"></path><path d="M13 19l6-6"></path><path d="M16 16l4 4"></path><path d="M19 21l2-2"></path><path d="M9.5 6.5L12 9"></path><path d="M6.5 9.5L9 12"></path></svg>`;

export function registerCombatNode(editor) {
  const getCombatHTML = `
    <div class="node-header node-header--combat">
      <span class="node-header__icon">${swordsSVG}</span>
      <span>COMBAT</span>
    </div>
    <div class="node-body">
      <div class="node-field">
        <label>Attack Type</label>
        <div class="node-preset-btns">
          <button class="node-preset-btn node-preset-btn--active" data-preset="melee">⚔️ Melee</button>
          <button class="node-preset-btn" data-preset="ranged">🏹 Ranged</button>
          <button class="node-preset-btn" data-preset="siege">💥 Siege</button>
        </div>
      </div>
      <div class="node-field">
        <label>Damage/sec</label>
        <input type="number" df-damage value="-10" class="node-input">
      </div>
      <div class="node-field">
        <label>Range</label>
        <input type="range" df-range min="5" max="200" value="15" class="node-slider">
        <span class="node-slider-value">15</span>
      </div>
      <div class="node-field">
        <label>Cooldown (ticks)</label>
        <input type="number" df-cooldownTicks value="0" min="0" class="node-input">
      </div>
    </div>
  `;

  registerNodeType('combat', {
    html: getCombatHTML,
    inputs: 3,
    outputs: 0,
  });

  editor.on('nodeCreated', (id) => {
    try {
      const node = editor.getNodeFromId(id);
      if (node.name === 'combat') {
        const currentData = { ...node.data };
        currentData.nodeType = 'combat';
        if (currentData.attackType === undefined) currentData.attackType = 'melee';
        if (currentData.damage === undefined) currentData.damage = -10;
        if (currentData.range === undefined) currentData.range = 15;
        if (currentData.cooldownTicks === undefined) currentData.cooldownTicks = 0;
        editor.updateNodeDataFromId(id, currentData);

        const nodeElement = document.getElementById(`node-${id}`);
        if (!nodeElement) return;

        const presetBtns = nodeElement.querySelectorAll('.node-preset-btn');
        const damageInput = nodeElement.querySelector('[df-damage]');
        const rangeInput = nodeElement.querySelector('[df-range]');
        const cooldownInput = nodeElement.querySelector('[df-cooldownTicks]');
        const rangeDisplay = nodeElement.querySelector('.node-slider-value');

        presetBtns.forEach(btn => {
          btn.addEventListener('click', (e) => {
            presetBtns.forEach(b => b.classList.remove('node-preset-btn--active'));
            e.target.classList.add('node-preset-btn--active');

            const preset = e.target.getAttribute('data-preset');
            let newDamage = -10;
            let newRange = 15;
            let newCooldown = 0;

            if (preset === 'melee') {
              newDamage = -10; newRange = 15; newCooldown = 0;
            } else if (preset === 'ranged') {
              newDamage = -5; newRange = 80; newCooldown = 0;
            } else if (preset === 'siege') {
              newDamage = -30; newRange = 40; newCooldown = 60;
            }

            damageInput.value = newDamage;
            rangeInput.value = newRange;
            cooldownInput.value = newCooldown;
            rangeDisplay.textContent = newRange;

            const updatedData = { ...editor.getNodeFromId(id).data };
            updatedData.attackType = preset;
            updatedData.damage = newDamage;
            updatedData.range = newRange;
            updatedData.cooldownTicks = newCooldown;
            editor.updateNodeDataFromId(id, updatedData);
          });
        });

        // Initialize active preset visually based on loaded data
        if (currentData.attackType) {
          presetBtns.forEach(b => b.classList.remove('node-preset-btn--active'));
          const btn = nodeElement.querySelector(`[data-preset="${currentData.attackType}"]`);
          if (btn) btn.classList.add('node-preset-btn--active');
        }

        // Initialize range display
        rangeDisplay.textContent = currentData.range || 15;
        
        rangeInput.addEventListener('input', (e) => {
            rangeDisplay.textContent = e.target.value;
        });
      }
    } catch(e) {
      // Handle missing nodes
    }
  });
}
