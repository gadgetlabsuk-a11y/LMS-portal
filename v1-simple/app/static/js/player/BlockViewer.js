// Read-only block renderer
function BlockViewer({ blocks }) {
  if (!blocks || blocks.length === 0) {
    return React.createElement('p', { className: 'player-empty' }, 'This slide has no content yet.');
  }
  return React.createElement('div', { className: 'block-viewer' },
    blocks.map(block => React.createElement(BlockView, { key: block.id, block }))
  );
}

function BlockView({ block }) {
  const p = block.props || {};
  switch (block.type) {
    case 'heading':
      return React.createElement(`h${p.level || 2}`, {
        className: 'bv-heading',
        style: { textAlign: p.align || 'left' },
      }, p.text || '');

    case 'paragraph':
      return React.createElement('div', {
        className: 'bv-paragraph',
        style: { textAlign: p.align || 'left' },
        dangerouslySetInnerHTML: { __html: p.text || '' },
      });

    case 'image':
      return React.createElement('figure', { className: 'bv-image' },
        React.createElement('img', { src: p.url || '', alt: p.alt || '', style: { objectFit: p.fit || 'contain' } }),
        p.caption && React.createElement('figcaption', null, p.caption)
      );

    case 'video':
      return React.createElement('video', {
        className: 'bv-video',
        controls: true,
        src: p.url || '',
        'aria-label': 'Course video',
      });

    case 'audio':
      return React.createElement('div', { className: 'bv-audio' },
        React.createElement('audio', { controls: true, src: p.url || '', 'aria-label': 'Course audio' }),
        p.transcript && React.createElement('details', null,
          React.createElement('summary', null, 'Transcript'),
          React.createElement('p', { className: 'bv-transcript' }, p.transcript)
        )
      );

    case 'divider':
      return React.createElement('hr', { className: 'bv-divider' });

    case 'spacer':
      return React.createElement('div', { style: { height: (p.height_px || 24) + 'px' } });

    case 'bullets':
      return React.createElement(p.style === 'number' ? 'ol' : 'ul', { className: 'bv-bullets' },
        (p.items || []).map((item, i) => React.createElement('li', { key: i }, item))
      );

    case 'button':
      return React.createElement('button', {
        className: 'bv-button',
        onClick: () => p.action === 'external' && p.url && window.open(p.url, '_blank'),
        'aria-label': p.label || 'Button',
      }, p.label || 'Button');

    case 'mcq_single':
    case 'mcq_multi':
      return React.createElement(QuizBlock, { block });

    case 'tf':
      return React.createElement(TrueFalseBlock, { block });

    default:
      return null;
  }
}

function QuizBlock({ block }) {
  const p = block.props || {};
  const isMulti = block.type === 'mcq_multi';
  const [selected, setSelected] = React.useState([]);
  const [submitted, setSubmitted] = React.useState(false);
  const [correct, setCorrect] = React.useState(null);

  function toggle(id) {
    if (submitted) return;
    if (isMulti) {
      setSelected(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id]);
    } else {
      setSelected([id]);
    }
  }

  function submit() {
    if (selected.length === 0) return;
    const correctIds = (p.options || []).filter(o => o.correct).map(o => o.id);
    const isCorrect = isMulti
      ? correctIds.every(id => selected.includes(id)) && selected.every(id => correctIds.includes(id))
      : selected[0] === correctIds[0];
    setCorrect(isCorrect);
    setSubmitted(true);
  }

  return React.createElement('div', { className: 'bv-quiz', role: 'group', 'aria-labelledby': `q-${block.id}` },
    React.createElement('p', { id: `q-${block.id}`, className: 'bv-question' }, p.question),
    (p.options || []).map(opt =>
      React.createElement('label', { key: opt.id, className: 'bv-option' + (submitted && opt.correct ? ' correct' : '') + (submitted && selected.includes(opt.id) && !opt.correct ? ' wrong' : '') },
        React.createElement('input', {
          type: isMulti ? 'checkbox' : 'radio',
          name: `q-${block.id}`,
          checked: selected.includes(opt.id),
          onChange: () => toggle(opt.id),
          disabled: submitted,
          'aria-label': opt.text,
        }),
        opt.text
      )
    ),
    !submitted && React.createElement('button', { onClick: submit, className: 'bv-submit', disabled: selected.length === 0 }, 'Submit'),
    submitted && React.createElement('div', { className: 'bv-feedback ' + (correct ? 'bv-correct' : 'bv-wrong'), role: 'alert' },
      correct ? '✓ Correct!' : '✗ Incorrect.',
      p.feedback && React.createElement('p', null, p.feedback)
    )
  );
}

function TrueFalseBlock({ block }) {
  const p = block.props || {};
  const [answer, setAnswer] = React.useState(null);
  const [submitted, setSubmitted] = React.useState(false);

  function submit() {
    if (answer === null) return;
    setSubmitted(true);
  }

  const isCorrect = answer === p.correct_answer;

  return React.createElement('div', { className: 'bv-quiz', role: 'group', 'aria-labelledby': `tf-${block.id}` },
    React.createElement('p', { id: `tf-${block.id}`, className: 'bv-question' }, p.question),
    ['true', 'false'].map(val =>
      React.createElement('label', { key: val, className: 'bv-option' },
        React.createElement('input', {
          type: 'radio', name: `tf-${block.id}`,
          checked: answer === (val === 'true'),
          onChange: () => !submitted && setAnswer(val === 'true'),
          disabled: submitted,
          'aria-label': val === 'true' ? 'True' : 'False',
        }),
        val === 'true' ? 'True' : 'False'
      )
    ),
    !submitted && React.createElement('button', { onClick: submit, className: 'bv-submit', disabled: answer === null }, 'Submit'),
    submitted && React.createElement('div', { className: 'bv-feedback ' + (isCorrect ? 'bv-correct' : 'bv-wrong'), role: 'alert' },
      isCorrect ? '✓ Correct!' : '✗ Incorrect.',
      p.feedback && React.createElement('p', null, p.feedback)
    )
  );
}
