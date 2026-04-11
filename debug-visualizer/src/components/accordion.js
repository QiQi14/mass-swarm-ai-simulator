// ─── Accordion Panel Component ────────────────────────────────

/**
 * @param {Object} opts
 * @param {string} opts.id
 * @param {string} opts.title
 * @param {string} [opts.icon='']
 * @param {boolean} [opts.expanded=false]
 * @returns {{ element: HTMLElement, body: HTMLElement, setExpanded: (v: boolean) => void }}
 */
export function createAccordion(opts) {
  const group = document.createElement('section');
  group.className = 'panel-group';
  group.id = `panel-${opts.id}`;
  group.dataset.panelId = opts.id;

  const header = document.createElement('div');
  header.className = 'panel-header';
  header.innerHTML = `
    <span class="panel-title">${opts.icon ? opts.icon + ' ' : ''}${opts.title}</span>
    <span class="panel-chevron">▸</span>
  `;

  const body = document.createElement('div');
  body.className = 'panel-body';

  const setExpanded = (expanded) => {
    if (expanded) {
      body.classList.add('expanded');
      body.classList.remove('collapsed');
      header.querySelector('.panel-chevron').textContent = '▾';
    } else {
      body.classList.remove('expanded');
      body.classList.add('collapsed');
      header.querySelector('.panel-chevron').textContent = '▸';
    }
  };

  header.onclick = () => {
    const isExpanded = body.classList.contains('expanded');
    setExpanded(!isExpanded);
  };

  setExpanded(opts.expanded ?? false);

  group.appendChild(header);
  group.appendChild(body);

  return { element: group, body, setExpanded };
}

/**
 * Show/hide panel groups based on mode.
 * @param {HTMLElement} container - The panel scroll container 
 * @param {string} mode - Current mode ('training' | 'playground')
 */
export function applyModeFilter(container, mode) {
  container.querySelectorAll('.panel-group').forEach(panel => {
    const modes = (panel.dataset.modes || '').split(',');
    const visible = modes.includes(mode) || modes.includes('both');
    panel.style.display = visible ? '' : 'none';
    // Add entrance animation
    if (visible) {
      panel.classList.add('mode-enter');
      requestAnimationFrame(() => {
        requestAnimationFrame(() => panel.classList.remove('mode-enter'));
      });
    }
  });
}
