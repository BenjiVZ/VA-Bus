/**
 * Aerorutas — Editor Visual de Asientos para Django Admin
 * Click/Drag grid editor for bus floor layouts.
 */
(function () {
  'use strict';

  const CELL_TYPES = {
    empty:  { label: '',     name: 'Vacío',    color: '#f4f5f7', border: '#dfe1e6', textColor: '#999' },
    seat:   { label: 'A',    name: 'Asiento',  color: '#ffffff', border: '#0052cc', textColor: '#0052cc' },
    aisle:  { label: '│',    name: 'Pasillo',  color: '#e8eaf0', border: '#b3bac5', textColor: '#b3bac5' },
    door:   { label: 'P',    name: 'Puerta',   color: '#fff3e0', border: '#e65100', textColor: '#e65100' },
    driver: { label: 'CH',   name: 'Chofer',   color: '#e3f2fd', border: '#1565c0', textColor: '#1565c0' },
    stairs: { label: 'ESC',  name: 'Escalera', color: '#e8f5e9', border: '#2e7d32', textColor: '#2e7d32' },
  };

  const TOOL_ICONS = {
    empty:  '▢',
    seat:   '◼',
    aisle:  '┃',
    door:   '▣',
    driver: '★',
    stairs: '▲',
  };

  let currentTool = 'seat';
  let isMouseDown = false;

  function init() {
    const layoutFields = document.querySelectorAll('textarea[id$="-layout"], textarea#id_layout');
    layoutFields.forEach(setupEditor);
  }

  function setupEditor(textarea) {
    textarea.style.display = 'none';

    const filasInput = findRelatedField(textarea, 'filas');
    const columnasInput = findRelatedField(textarea, 'columnas');

    if (!filasInput || !columnasInput) {
      console.warn('seat_editor: No se encontraron campos filas/columnas');
      return;
    }

    const editorWrap = document.createElement('div');
    editorWrap.className = 'seat-editor-wrap';
    editorWrap.innerHTML = `
      <div class="seat-editor-toolbar">
        <span class="seat-editor-title">🚌 Editor de Layout</span>
        <div class="seat-editor-tools">
          ${Object.entries(CELL_TYPES).map(([key, val]) => `
            <button type="button" class="seat-tool ${key === currentTool ? 'active' : ''}" data-tool="${key}"
                    style="--tool-color: ${val.border}; --tool-bg: ${val.color};">
              <span class="tool-icon">${TOOL_ICONS[key]}</span>
              <span class="tool-name">${val.name}</span>
            </button>
          `).join('')}
        </div>
        <div class="seat-editor-actions">
          <button type="button" class="seat-action-btn" id="btn-autonumber-${textarea.id}">
            # Auto-Numerar
          </button>
          <button type="button" class="seat-action-btn seat-action-btn-danger" id="btn-clear-${textarea.id}">
            ✕ Limpiar
          </button>
        </div>
      </div>
      <div class="seat-editor-grid-container">
        <div class="seat-editor-grid" id="grid-${textarea.id}"></div>
      </div>
      <div class="seat-editor-status" id="status-${textarea.id}">0 asientos</div>
    `;

    textarea.parentNode.insertBefore(editorWrap, textarea.nextSibling);

    const grid = editorWrap.querySelector('.seat-editor-grid');
    const statusEl = editorWrap.querySelector('.seat-editor-status');

    // Tool selection
    editorWrap.querySelectorAll('.seat-tool').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        currentTool = btn.dataset.tool;
        editorWrap.querySelectorAll('.seat-tool').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });

    // Auto-number
    editorWrap.querySelector(`#btn-autonumber-${textarea.id}`).addEventListener('click', (e) => {
      e.preventDefault();
      autoNumber(textarea, grid, statusEl);
    });

    // Clear
    editorWrap.querySelector(`#btn-clear-${textarea.id}`).addEventListener('click', (e) => {
      e.preventDefault();
      clearGrid(textarea, filasInput, columnasInput, grid, statusEl);
    });

    // Filas/columnas changes
    const rebuildFn = () => rebuildGrid(textarea, filasInput, columnasInput, grid, statusEl);
    filasInput.addEventListener('change', rebuildFn);
    columnasInput.addEventListener('change', rebuildFn);

    document.addEventListener('mouseup', () => { isMouseDown = false; });

    rebuildGrid(textarea, filasInput, columnasInput, grid, statusEl);
  }

  function findRelatedField(textarea, fieldName) {
    // look for field in same inline group
    const inlineForm = textarea.closest('.inline-related, .djn-inline-form, .dynamic-pisos_config');
    if (inlineForm) {
      const input = inlineForm.querySelector(`input[name$="-${fieldName}"]`);
      if (input) return input;
    }
    // fallback
    return document.querySelector(`input[name$="-${fieldName}"], input[name="${fieldName}"]`);
  }

  function rebuildGrid(textarea, filasInput, columnasInput, gridEl, statusEl) {
    const filas = parseInt(filasInput.value) || 10;
    const columnas = parseInt(columnasInput.value) || 5;

    let existingLayout = [];
    try {
      existingLayout = JSON.parse(textarea.value);
      if (!Array.isArray(existingLayout)) existingLayout = [];
    } catch (e) {
      existingLayout = [];
    }

    gridEl.innerHTML = '';
    gridEl.style.gridTemplateColumns = `repeat(${columnas}, 56px)`;

    for (let r = 0; r < filas; r++) {
      for (let c = 0; c < columnas; c++) {
        const cell = (existingLayout[r] && existingLayout[r][c]) || { type: 'empty' };
        const cellEl = createCellElement(cell, r, c);

        cellEl.addEventListener('mousedown', (e) => {
          e.preventDefault();
          isMouseDown = true;
          applyTool(cellEl, textarea, gridEl, statusEl);
        });

        cellEl.addEventListener('mouseenter', () => {
          if (isMouseDown) {
            applyTool(cellEl, textarea, gridEl, statusEl);
          }
        });

        gridEl.appendChild(cellEl);
      }
    }

    updateStatus(gridEl, statusEl);
  }

  function createCellElement(cell, row, col) {
    const el = document.createElement('div');
    el.className = 'seat-cell';
    el.dataset.row = row;
    el.dataset.col = col;
    el.dataset.type = cell.type || 'empty';
    el.dataset.number = cell.number || '';
    applyCellStyle(el);
    return el;
  }

  function applyCellStyle(el) {
    const type = el.dataset.type;
    const info = CELL_TYPES[type] || CELL_TYPES.empty;
    el.style.backgroundColor = info.color;
    el.style.borderColor = info.border;
    el.style.color = info.textColor;

    if (type === 'seat' && el.dataset.number) {
      el.textContent = el.dataset.number;
      el.className = 'seat-cell seat-cell-numbered';
    } else if (type === 'empty') {
      el.textContent = '';
      el.className = 'seat-cell seat-cell-empty';
    } else {
      el.textContent = info.label;
      el.className = 'seat-cell seat-cell-typed';
    }
  }

  function applyTool(cellEl, textarea, gridEl, statusEl) {
    cellEl.dataset.type = currentTool;
    if (currentTool !== 'seat') {
      cellEl.dataset.number = '';
    }
    applyCellStyle(cellEl);
    saveLayout(textarea, gridEl);
    updateStatus(gridEl, statusEl);
  }

  function autoNumber(textarea, gridEl, statusEl) {
    let num = 1;
    gridEl.querySelectorAll('.seat-cell').forEach(cell => {
      if (cell.dataset.type === 'seat') {
        cell.dataset.number = num++;
        applyCellStyle(cell);
      }
    });
    saveLayout(textarea, gridEl);
    updateStatus(gridEl, statusEl);
  }

  function clearGrid(textarea, filasInput, columnasInput, gridEl, statusEl) {
    gridEl.querySelectorAll('.seat-cell').forEach(cell => {
      cell.dataset.type = 'empty';
      cell.dataset.number = '';
      applyCellStyle(cell);
    });
    saveLayout(textarea, gridEl);
    updateStatus(gridEl, statusEl);
  }

  function saveLayout(textarea, gridEl) {
    const cells = gridEl.querySelectorAll('.seat-cell');
    const layout = [];
    let currentRow = -1;

    cells.forEach(cell => {
      const r = parseInt(cell.dataset.row);
      if (r !== currentRow) {
        layout.push([]);
        currentRow = r;
      }
      const cellData = { type: cell.dataset.type };
      if (cell.dataset.type === 'seat' && cell.dataset.number) {
        cellData.number = parseInt(cell.dataset.number);
      }
      layout[layout.length - 1].push(cellData);
    });

    textarea.value = JSON.stringify(layout);
  }

  function updateStatus(gridEl, statusEl) {
    let seats = 0, doors = 0, driver = 0;
    gridEl.querySelectorAll('.seat-cell').forEach(cell => {
      if (cell.dataset.type === 'seat') seats++;
      if (cell.dataset.type === 'door') doors++;
      if (cell.dataset.type === 'driver') driver++;
    });
    const parts = [`${seats} asiento${seats !== 1 ? 's' : ''}`];
    if (doors > 0) parts.push(`${doors} puerta${doors !== 1 ? 's' : ''}`);
    if (driver > 0) parts.push(`${driver} chofer`);
    statusEl.textContent = parts.join(' · ');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Re-init for new inline forms
  const observer = new MutationObserver((mutations) => {
    mutations.forEach(m => {
      m.addedNodes.forEach(node => {
        if (node.nodeType === 1) {
          const textareas = node.querySelectorAll ?
            node.querySelectorAll('textarea[id$="-layout"]') : [];
          textareas.forEach(setupEditor);
        }
      });
    });
  });
  const inlineGroup = document.querySelector('.inline-group, #pisos_config-group');
  if (inlineGroup) observer.observe(inlineGroup, { childList: true, subtree: true });
})();
