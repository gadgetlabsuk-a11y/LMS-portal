// Block Editor — main canvas
function BlockEditor({ courseId, slide, onSave }) {
  const [blocks, setBlocks] = React.useState(slide?.blocks || []);
  const [saving, setSaving] = React.useState(false);
  const [status, setStatus] = React.useState('');
  const saveTimer = React.useRef(null);

  React.useEffect(() => {
    setBlocks(slide?.blocks || []);
  }, [slide?.id]);

  function updateBlock(id, newProps) {
    setBlocks(prev => prev.map(b => b.id === id ? { ...b, props: { ...b.props, ...newProps } } : b));
    scheduleSave();
  }

  function removeBlock(id) {
    setBlocks(prev => prev.filter(b => b.id !== id));
    scheduleSave();
  }

  function addBlock(type) {
    const id = 'b_' + Math.random().toString(36).slice(2, 10);
    const newBlock = {
      id,
      type,
      props: defaultProps(type),
      layout: { col_start: 1, col_span: 12, row_start: blocks.length + 1, row_span: 1 },
    };
    setBlocks(prev => [...prev, newBlock]);
    scheduleSave();
  }

  function moveBlock(fromIdx, toIdx) {
    setBlocks(prev => {
      const arr = [...prev];
      const [item] = arr.splice(fromIdx, 1);
      arr.splice(toIdx, 0, item);
      return arr.map((b, i) => ({ ...b, layout: { ...b.layout, row_start: i + 1 } }));
    });
    scheduleSave();
  }

  function scheduleSave() {
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(doSave, 2000);
  }

  async function doSave() {
    if (!slide) return;
    setSaving(true);
    try {
      await LmsApi.apiFetch(`/api/slides/${slide.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ blocks }),
      });
      setStatus('Saved');
      setTimeout(() => setStatus(''), 2000);
    } catch (e) {
      setStatus('Save failed: ' + e.message);
    } finally {
      setSaving(false);
    }
  }

  if (!slide) return React.createElement('div', { className: 'editor-empty' }, 'Select a slide to edit');

  return React.createElement('div', { className: 'block-editor' },
    React.createElement('div', {
      className: 'editor-status',
      role: 'status',
      'aria-live': 'polite',
    }, saving ? 'Saving…' : status),
    React.createElement('div', { className: 'editor-canvas' },
      blocks.map((block, idx) =>
        React.createElement(BlockEditorItem, {
          key: block.id,
          block,
          index: idx,
          total: blocks.length,
          onUpdate: (props) => updateBlock(block.id, props),
          onRemove: () => removeBlock(block.id),
          onMoveUp: idx > 0 ? () => moveBlock(idx, idx - 1) : null,
          onMoveDown: idx < blocks.length - 1 ? () => moveBlock(idx, idx + 1) : null,
        })
      )
    ),
    React.createElement(BlockPaletteInline, { onAdd: addBlock })
  );
}

function defaultProps(type) {
  const defaults = {
    heading: { text: 'New Heading', level: 2, align: 'left' },
    paragraph: { text: 'Enter text here…', align: 'left' },
    image: { alt: '', caption: '', fit: 'contain' },
    video: { url: '', controls: true, autoplay: false },
    audio: { transcript: '', controls: true },
    divider: { style: 'solid', thickness: 1 },
    spacer: { height_px: 24 },
    bullets: { items: ['Item 1', 'Item 2'], style: 'bullet' },
    accordion: { panels: [{ title: 'Section 1', body_blocks: [] }] },
    button: { label: 'Next', action: 'next' },
    mcq_single: { question: 'Question?', options: [{ id: 'a', text: 'Option A', correct: true }, { id: 'b', text: 'Option B', correct: false }], feedback: '', points: 1 },
    mcq_multi: { question: 'Question?', options: [{ id: 'a', text: 'Option A', correct: true }, { id: 'b', text: 'Option B', correct: false }], feedback: '', points: 2 },
    tf: { question: 'True or False?', correct_answer: true, feedback: '', points: 1 },
  };
  return defaults[type] || {};
}

function BlockEditorItem({ block, index, total, onUpdate, onRemove, onMoveUp, onMoveDown }) {
  const [expanded, setExpanded] = React.useState(true);

  return React.createElement('div', {
    className: 'block-item',
    'data-type': block.type,
    role: 'region',
    'aria-label': `${block.type} block`,
  },
    React.createElement('div', { className: 'block-toolbar' },
      React.createElement('span', { className: 'block-type-label' }, block.type),
      React.createElement('div', { className: 'block-actions' },
        onMoveUp && React.createElement('button', { onClick: onMoveUp, 'aria-label': 'Move block up', title: 'Move up' }, '↑'),
        onMoveDown && React.createElement('button', { onClick: onMoveDown, 'aria-label': 'Move block down', title: 'Move down' }, '↓'),
        React.createElement('button', { onClick: () => setExpanded(e => !e), 'aria-label': expanded ? 'Collapse block' : 'Expand block' }, expanded ? '−' : '+'),
        React.createElement('button', { onClick: onRemove, 'aria-label': 'Remove block', className: 'btn-danger' }, '×'),
      )
    ),
    expanded && React.createElement(BlockFieldEditor, { block, onUpdate })
  );
}

function BlockFieldEditor({ block, onUpdate }) {
  const p = block.props;
  const field = (label, key, type = 'text', extra = {}) =>
    React.createElement('label', { className: 'field', key },
      React.createElement('span', null, label),
      React.createElement('input', {
        type,
        value: p[key] ?? '',
        onChange: e => onUpdate({ [key]: type === 'number' ? Number(e.target.value) : e.target.value }),
        ...extra,
      })
    );

  switch (block.type) {
    case 'heading':
      return React.createElement('div', { className: 'block-fields' },
        field('Text', 'text'),
        React.createElement('label', { className: 'field' }, 'Level',
          React.createElement('select', { value: p.level || 2, onChange: e => onUpdate({ level: Number(e.target.value) }) },
            [1,2,3].map(l => React.createElement('option', { key: l, value: l }, `H${l}`))
          )
        )
      );
    case 'paragraph':
      return React.createElement('div', { className: 'block-fields' },
        React.createElement('label', { className: 'field' }, 'Text',
          React.createElement('textarea', {
            value: p.text || '',
            rows: 4,
            onChange: e => onUpdate({ text: e.target.value }),
          })
        )
      );
    case 'image':
      return React.createElement('div', { className: 'block-fields' },
        field('Alt text (required)', 'alt'),
        field('Caption', 'caption'),
      );
    case 'audio':
      return React.createElement('div', { className: 'block-fields' },
        field('Transcript (required for accessibility)', 'transcript'),
      );
    case 'video':
      return React.createElement('div', { className: 'block-fields' },
        field('Video URL', 'url'),
        field('Transcript', 'transcript'),
      );
    case 'bullets':
      return React.createElement('div', { className: 'block-fields' },
        React.createElement('label', { className: 'field' }, 'Items (one per line)',
          React.createElement('textarea', {
            value: (p.items || []).join('\n'),
            rows: 4,
            onChange: e => onUpdate({ items: e.target.value.split('\n') }),
          })
        )
      );
    case 'mcq_single':
    case 'mcq_multi':
      return React.createElement('div', { className: 'block-fields' },
        field('Question', 'question'),
        React.createElement('p', { className: 'field-hint' }, 'Options editing — use the API directly for now'),
        field('Feedback', 'feedback'),
      );
    case 'tf':
      return React.createElement('div', { className: 'block-fields' },
        field('Question', 'question'),
        React.createElement('label', { className: 'field' }, 'Correct answer',
          React.createElement('select', { value: String(p.correct_answer), onChange: e => onUpdate({ correct_answer: e.target.value === 'true' }) },
            React.createElement('option', { value: 'true' }, 'True'),
            React.createElement('option', { value: 'false' }, 'False'),
          )
        ),
        field('Feedback', 'feedback'),
      );
    case 'button':
      return React.createElement('div', { className: 'block-fields' },
        field('Label', 'label'),
        React.createElement('label', { className: 'field' }, 'Action',
          React.createElement('select', { value: p.action || 'next', onChange: e => onUpdate({ action: e.target.value }) },
            ['next','prev','external','complete'].map(a => React.createElement('option', { key: a, value: a }, a))
          )
        ),
        p.action === 'external' && field('URL', 'url'),
      );
    case 'spacer':
      return React.createElement('div', { className: 'block-fields' },
        field('Height (px)', 'height_px', 'number'),
      );
    default:
      return React.createElement('p', { className: 'field-hint' }, `No editor for ${block.type}`);
  }
}

function BlockPaletteInline({ onAdd }) {
  const BLOCK_TYPES = [
    ['heading','Heading'],['paragraph','Paragraph'],['image','Image'],
    ['video','Video'],['audio','Audio'],['divider','Divider'],['spacer','Spacer'],
    ['bullets','Bullets'],['accordion','Accordion'],['button','Button'],
    ['mcq_single','MCQ Single'],['mcq_multi','MCQ Multi'],['tf','True/False'],
  ];
  return React.createElement('div', { className: 'block-palette', role: 'toolbar', 'aria-label': 'Add block' },
    React.createElement('span', { className: 'palette-label' }, '+ Add block:'),
    ...BLOCK_TYPES.map(([type, label]) =>
      React.createElement('button', {
        key: type,
        className: 'palette-btn',
        onClick: () => onAdd(type),
        'aria-label': `Add ${label} block`,
      }, label)
    )
  );
}
