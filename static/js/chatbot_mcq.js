/**
 * chatbot_mcq.js — QuizX AI Quiz Builder (Multi-Type)
 * ────────────────────────────────────────────────────
 * Supports: MCQ, True/False, Short Answer, Checkbox, Mixed
 * Features: Edit, Delete, Copy, Drag-reorder, Generate More,
 *           Explanation, Type badges, Timestamps, Add-to-Quiz
 * ────────────────────────────────────────────────────
 */
(function () {
    'use strict';

    const STORAGE_KEY = 'quizQuestions';
    const TYPE_COLORS = {
        mcq: { bg: 'rgba(91,163,58,.1)', text: '#5ba33a', label: 'MCQ' },
        true_false: { bg: 'rgba(168,85,247,.1)', text: '#a855f7', label: 'True/False' },
        short_answer: { bg: 'rgba(59,130,246,.1)', text: '#3b82f6', label: 'Short Answer' },
        checkbox: { bg: 'rgba(245,158,11,.1)', text: '#f59e0b', label: 'Checkbox' }
    };

    /* ──── Page detection ──── */
    function isOnAddQuestionPage() {
        return /\/admin\/add-question\/\d+/.test(window.location.pathname);
    }

    /* ──── localStorage ──── */
    function getSaved()  { try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); } catch (_) { return []; } }
    function setSaved(l) { localStorage.setItem(STORAGE_KEY, JSON.stringify(l)); }
    function clearSaved() { localStorage.removeItem(STORAGE_KEY); }

    function storeOne(q) {
        const list = getSaved();
        if (list.some(x => x.question === q.question)) return false;
        list.push(q); setSaved(list); return true;
    }
    function storeMany(qs) {
        const list = getSaved(); let n = 0;
        qs.forEach(q => { if (!list.some(x => x.question === q.question)) { list.push(q); n++; } });
        setSaved(list); return n;
    }

    /* ──── Escape HTML ──── */
    function esc(s) { const d = document.createElement('div'); d.appendChild(document.createTextNode(s || '')); return d.innerHTML; }

    /* ──── Toast ──── */
    function showToast(msg, isErr) {
        const old = document.getElementById('mcq-toast'); if (old) old.remove();
        const t = document.createElement('div'); t.id = 'mcq-toast';
        Object.assign(t.style, {
            position:'fixed',bottom:'100px',right:'32px',zIndex:'99999',
            background:isErr?'#ef4444':'#22c55e',color:'#fff',
            padding:'12px 24px',borderRadius:'12px',fontWeight:'600',
            fontSize:'0.85rem',boxShadow:'0 6px 20px rgba(0,0,0,.25)',
            transition:'opacity .3s',fontFamily:"'Plus Jakarta Sans',sans-serif"
        });
        t.textContent = msg; document.body.appendChild(t);
        setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 2500);
    }

    /* ──── Copy to clipboard ──── */
    function copyText(text) {
        navigator.clipboard.writeText(text).then(() => showToast('Copied!')).catch(() => showToast('Copy failed', true));
    }

    /* ──── Timestamp ──── */
    function timeNow() {
        return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    /* ════════════════════════════════════════════════
     *  FORM INSERT — Mode A (Multi-Type)
     * ════════════════════════════════════════════════ */
    function insertIntoForm(q) {
        const container = document.getElementById('questions-container');
        if (!container) return false;
        const blocks = container.querySelectorAll('.question-block');
        const first = blocks[0];
        const firstEditor = first ? first.querySelector('.editor') : null;
        const firstHidden = first ? first.querySelector("input[type='hidden'][name='question[]']") : null;
        const isEmpty = firstEditor && !firstEditor.textContent.trim() && firstHidden && !firstHidden.value.trim();
        let target;
        if (blocks.length === 1 && isEmpty) {
            target = first;
        } else {
            if (typeof window.addQuestion === 'function') {
                const hasTimer = !!first.querySelector('.timer-input-group');
                window.addQuestion(hasTimer);
            }
            const all = container.querySelectorAll('.question-block');
            target = all[all.length - 1];
        }
        if (!target) return false;
        fillBlock(target, q);
        return true;
    }

    function fillBlock(block, q) {
        const qtype = q.type || 'mcq';
        // Question text
        const ed = block.querySelector('.editor');
        const hid = block.querySelector("input[type='hidden'][name='question[]']");
        if (ed) ed.textContent = q.question || '';
        if (hid) hid.value = q.question || '';

        // Set question type and trigger change
        const sel = block.querySelector('.q-type-group select');
        if (sel) {
            sel.value = qtype;
            // Find block index to call changeQuestionType
            const allBlocks = block.parentElement.querySelectorAll('.question-block');
            let idx = 0;
            allBlocks.forEach((b, i) => { if (b === block) idx = i; });
            if (typeof window.changeQuestionType === 'function') {
                window.changeQuestionType(sel, idx);
            }
        }

        if (qtype === 'mcq') {
            const opts = q.options || [];
            const inputs = block.querySelectorAll('.options-grid input[type="text"]');
            for (let i = 0; i < 4; i++) { if (inputs[i] && opts[i]) inputs[i].value = opts[i]; }
            const v = (q.correct_answer || 'A').charCodeAt(0) - 64;
            const r = block.querySelector("input[type='radio'][value='" + v + "']");
            if (r) r.checked = true;

        } else if (qtype === 'checkbox') {
            const opts = q.options || [];
            const inputs = block.querySelectorAll('.options-grid input[type="text"]');
            for (let i = 0; i < 4; i++) { if (inputs[i] && opts[i]) inputs[i].value = opts[i]; }
            // Check correct answer checkboxes
            const letters = q.correct_answer_letters || [];
            letters.forEach(l => {
                const v = l.charCodeAt(0) - 64;
                const cb = block.querySelector("input[type='checkbox'][value='" + v + "']");
                if (cb) cb.checked = true;
            });

        } else if (qtype === 'true_false') {
            const ans = q.correct_answer || 'True';
            const r = block.querySelector("input[type='radio'][value='" + ans + "']");
            if (r) r.checked = true;

        } else if (qtype === 'short_answer') {
            const inp = block.querySelector('.short-answer-wrapper input[type="text"]');
            if (inp) inp.value = q.correct_answer || '';
        }
    }

    /* ──── Create quiz + redirect (Mode B) ──── */
    async function createQuizAndRedirect(title) {
        try {
            const r = await fetch('/api/create-quiz-from-ai', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({ title })
            });
            const d = await r.json();
            if (d.success && d.quiz_id) window.location.href = '/admin/add-question/' + d.quiz_id;
            else showToast(d.error || 'Failed to create quiz', true);
        } catch (_) { showToast('Network error creating quiz', true); }
    }

    /* ════════════════════════════════════════════════
     *  BUILD CARD VIEW per question type
     * ════════════════════════════════════════════════ */
    function buildCardBody(q) {
        const labels = ['A','B','C','D'];
        const qtype = q.type || 'mcq';

        let html = '';
        if (qtype === 'mcq') {
            html = (q.options || []).map((opt, oi) => {
                const correct = String.fromCharCode(65 + oi) === q.correct_answer;
                return `<div class="qcard-opt${correct?' qcard-opt-correct':''}">
                    <span class="qcard-opt-label${correct?' correct':''}">${labels[oi]}</span>
                    <span class="qcard-opt-text">${esc(opt)}</span>
                    ${correct?'<span class="qcard-correct-badge">&#10003; Correct</span>':''}
                </div>`;
            }).join('');

        } else if (qtype === 'checkbox') {
            const correctLetters = q.correct_answer_letters || [];
            html = (q.options || []).map((opt, oi) => {
                const letter = String.fromCharCode(65 + oi);
                const correct = correctLetters.includes(letter);
                return `<div class="qcard-opt${correct?' qcard-opt-correct':''}">
                    <span class="qcard-opt-label${correct?' correct':''}">${labels[oi]}</span>
                    <span class="qcard-opt-text">${esc(opt)}</span>
                    ${correct?'<span class="qcard-correct-badge">&#10003;</span>':''}
                </div>`;
            }).join('');

        } else if (qtype === 'true_false') {
            ['True','False'].forEach(v => {
                const correct = q.correct_answer === v;
                html += `<div class="qcard-opt${correct?' qcard-opt-correct':''}">
                    <span class="qcard-opt-label${correct?' correct':''}">${v === 'True' ? 'T' : 'F'}</span>
                    <span class="qcard-opt-text">${v}</span>
                    ${correct?'<span class="qcard-correct-badge">&#10003; Correct</span>':''}
                </div>`;
            });

        } else if (qtype === 'short_answer') {
            html = `<div class="qcard-short-ans">
                <span class="qcard-ans-label">Answer:</span>
                <span class="qcard-ans-value">${esc(q.correct_answer || '')}</span>
            </div>`;
        }

        if (q.explanation) {
            html += `<div class="qcard-explanation">
                <strong>Explanation</strong><br>${esc(q.explanation)}
            </div>`;
        }
        return html;
    }

    /* ════════════════════════════════════════════════
     *  BUILD EDIT MODE per question type
     * ════════════════════════════════════════════════ */
    function buildEditHTML(q) {
        const labels = ['A','B','C','D'];
        const qtype = q.type || 'mcq';
        let html = `<div class="qcard-edit-form">
            <label class="qcard-edit-label">Question</label>
            <textarea class="eq-text qcard-edit-textarea">${esc(q.question)}</textarea>`;

        if (qtype === 'mcq') {
            html += labels.map((l, i) => `
                <div class="qcard-edit-opt-row">
                    <input type="radio" name="eq-correct-${q._id}" value="${l}" ${l===q.correct_answer?'checked':''} class="qcard-radio">
                    <input type="text" class="eq-opt qcard-edit-input" data-oi="${i}" value="${esc((q.options||[])[i]||'')}">
                    <span class="qcard-edit-opt-label">${l}</span>
                </div>`).join('');

        } else if (qtype === 'checkbox') {
            const correctLetters = q.correct_answer_letters || [];
            html += labels.map((l, i) => `
                <div class="qcard-edit-opt-row">
                    <input type="checkbox" name="eq-correct-${q._id}" value="${l}" ${correctLetters.includes(l)?'checked':''} class="qcard-checkbox">
                    <input type="text" class="eq-opt qcard-edit-input" data-oi="${i}" value="${esc((q.options||[])[i]||'')}">
                    <span class="qcard-edit-opt-label">${l}</span>
                </div>`).join('');

        } else if (qtype === 'true_false') {
            html += `<div class="qcard-edit-opt-row">
                <input type="radio" name="eq-correct-${q._id}" value="True" ${q.correct_answer==='True'?'checked':''} class="qcard-radio"> True
                <input type="radio" name="eq-correct-${q._id}" value="False" ${q.correct_answer==='False'?'checked':''} class="qcard-radio" style="margin-left:16px;"> False
            </div>`;

        } else if (qtype === 'short_answer') {
            html += `<label class="qcard-edit-label">Answer</label>
                <input type="text" class="eq-short-ans qcard-edit-input" value="${esc(q.correct_answer||'')}">`;
        }

        html += `<label class="qcard-edit-label">Explanation</label>
            <textarea class="eq-expl qcard-edit-textarea small">${esc(q.explanation||'')}</textarea>
            <div class="qcard-edit-actions">
                <button class="btn-cancel-edit qcard-btn-cancel">Cancel</button>
                <button class="btn-save-edit qcard-btn-save">Save</button>
            </div>
        </div>`;
        return html;
    }

    function saveEdit(editMode, q) {
        const qtype = q.type || 'mcq';
        q.question = editMode.querySelector('.eq-text').value.trim();
        q.explanation = editMode.querySelector('.eq-expl').value.trim();

        if (qtype === 'mcq') {
            editMode.querySelectorAll('.eq-opt').forEach(inp => {
                q.options[parseInt(inp.dataset.oi)] = inp.value.trim();
            });
            const checked = editMode.querySelector('input[type="radio"]:checked');
            if (checked) q.correct_answer = checked.value;

        } else if (qtype === 'checkbox') {
            editMode.querySelectorAll('.eq-opt').forEach(inp => {
                q.options[parseInt(inp.dataset.oi)] = inp.value.trim();
            });
            const checked = editMode.querySelectorAll('input[type="checkbox"]:checked');
            q.correct_answer_letters = Array.from(checked).map(c => c.value);
            q.correct_answers = q.correct_answer_letters.map(l => q.options[l.charCodeAt(0) - 65]);

        } else if (qtype === 'true_false') {
            const checked = editMode.querySelector('input[type="radio"]:checked');
            if (checked) q.correct_answer = checked.value;

        } else if (qtype === 'short_answer') {
            q.correct_answer = editMode.querySelector('.eq-short-ans').value.trim();
        }
    }

    /* ════════════════════════════════════════════════
     *  MAIN PANEL BUILDER
     * ════════════════════════════════════════════════ */
    function buildQuizPanel(questions, quizMeta) {
        const onPage = isOnAddQuestionPage();
        const topic = quizMeta.topic || '';
        const title = quizMeta.title || 'AI Generated Quiz';
        const qTypeFromMeta = quizMeta.question_type || 'mcq';

        let qList = questions.map((q, i) => ({ ...q, _id: i }));
        let nextId = questions.length;

        const root = document.createElement('div');
        root.className = 'qx-quiz-panel';

        /* ── Header bar with count + timestamp ── */
        const hdr = document.createElement('div');
        hdr.className = 'qx-panel-header';
        hdr.innerHTML = `<span class="qx-panel-count">${qList.length} question(s)</span>
            <span class="qx-panel-time">${timeNow()}</span>`;
        root.appendChild(hdr);

        /* ── Cards container ── */
        const cardsContainer = document.createElement('div');
        cardsContainer.className = 'qx-cards-container';
        root.appendChild(cardsContainer);

        function renderCards() {
            cardsContainer.innerHTML = '';
            hdr.querySelector('.qx-panel-count').textContent = qList.length + ' question(s)';
            qList.forEach((q, idx) => cardsContainer.appendChild(buildCard(q, idx)));
            initDragDrop();
        }

        function buildCard(q, idx) {
            const qtype = q.type || 'mcq';
            const tc = TYPE_COLORS[qtype] || TYPE_COLORS.mcq;

            const card = document.createElement('div');
            card.className = 'qx-qcard';
            card.draggable = true;
            card.dataset.qid = q._id;

            card.innerHTML = `
                <div class="qx-qcard-top">
                    <div class="qx-qcard-left">
                        <i class="fas fa-grip-vertical qx-grip"></i>
                        <span class="qx-qcard-num">Q${idx+1}</span>
                        <span class="qx-qcard-type" style="background:${tc.bg};color:${tc.text};">${tc.label}</span>
                    </div>
                    <div class="qx-qcard-actions">
                        <button class="btn-copy-q qx-icon-btn" title="Copy"><i class="fas fa-copy"></i></button>
                        <button class="btn-edit-q qx-icon-btn" title="Edit"><i class="fas fa-pen"></i></button>
                        <button class="btn-del-q qx-icon-btn del" title="Delete"><i class="fas fa-trash"></i></button>
                    </div>
                </div>
                <div class="q-view-mode">
                    <div class="qx-qcard-question">${esc(q.question)}</div>
                    <div class="qx-qcard-body">${buildCardBody(q)}</div>
                </div>
                <div class="q-edit-mode" style="display:none;"></div>
                <div class="qx-qcard-bottom">
                    <button class="btn-add-one qx-btn-add"><i class="fas fa-plus"></i> Add to Quiz</button>
                </div>`;

            // Copy
            card.querySelector('.btn-copy-q').addEventListener('click', e => {
                e.stopPropagation();
                const txt = q.question + '\n' + (q.options||[]).map((o,i) => String.fromCharCode(65+i)+'. '+o).join('\n')
                    + '\nAnswer: ' + (q.correct_answer||'');
                copyText(txt);
            });

            // Edit
            card.querySelector('.btn-edit-q').addEventListener('click', e => {
                e.stopPropagation();
                const viewMode = card.querySelector('.q-view-mode');
                const editMode = card.querySelector('.q-edit-mode');
                if (editMode.style.display === 'none') {
                    viewMode.style.display = 'none';
                    editMode.style.display = 'block';
                    card.draggable = false;
                    editMode.innerHTML = buildEditHTML(q);
                    editMode.querySelector('.btn-cancel-edit').addEventListener('click', () => {
                        viewMode.style.display = 'block'; editMode.style.display = 'none'; card.draggable = true;
                    });
                    editMode.querySelector('.btn-save-edit').addEventListener('click', () => {
                        saveEdit(editMode, q); renderCards(); showToast('Question updated');
                    });
                } else {
                    viewMode.style.display = 'block'; editMode.style.display = 'none'; card.draggable = true;
                }
            });

            // Delete
            card.querySelector('.btn-del-q').addEventListener('click', e => {
                e.stopPropagation();
                qList = qList.filter(x => x._id !== q._id);
                renderCards(); showToast('Question removed');
            });

            // Add to Quiz
            const addBtn = card.querySelector('.btn-add-one');
            addBtn.addEventListener('click', () => {
                const ok = onPage ? insertIntoForm(q) : storeOne(q);
                if (ok) {
                    showToast(onPage ? `Q${idx+1} inserted!` : `Q${idx+1} saved`);
                    addBtn.innerHTML = '&#10003; Added'; addBtn.disabled = true; addBtn.classList.add('added');
                } else {
                    showToast('Already added', true);
                }
            });

            return card;
        }

        /* ── Drag & Drop ── */
        let dragSrc = null;
        function initDragDrop() {
            cardsContainer.querySelectorAll('.qx-qcard').forEach(card => {
                card.addEventListener('dragstart', function(e) { dragSrc = this; this.classList.add('dragging'); e.dataTransfer.effectAllowed = 'move'; });
                card.addEventListener('dragend', function() { this.classList.remove('dragging'); dragSrc = null; });
                card.addEventListener('dragover', function(e) { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; });
                card.addEventListener('drop', function(e) {
                    e.preventDefault(); if (dragSrc === this) return;
                    const fid = parseInt(dragSrc.dataset.qid), tid = parseInt(this.dataset.qid);
                    const fi = qList.findIndex(x=>x._id===fid), ti = qList.findIndex(x=>x._id===tid);
                    if (fi<0||ti<0) return;
                    const [m] = qList.splice(fi,1); qList.splice(ti,0,m); renderCards();
                });
            });
        }

        /* ── Action bar ── */
        const actBar = document.createElement('div');
        actBar.className = 'qx-panel-actions';

        // Generate More
        const genBtn = document.createElement('button');
        genBtn.className = 'qx-btn-generate';
        genBtn.innerHTML = '<i class="fas fa-wand-magic-sparkles"></i> Generate 10 More';
        genBtn.addEventListener('click', async () => {
            genBtn.disabled = true;
            genBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating…';
            try {
                const res = await fetch('/api/generate-mcq', {
                    method:'POST', headers:{'Content-Type':'application/json'},
                    body: JSON.stringify({ prompt: topic, difficulty: (quizMeta.difficulty||'medium').toLowerCase(), question_type: qTypeFromMeta })
                });
                const data = await res.json();
                if (data.success && data.data && data.data.questions) {
                    let added = 0;
                    data.data.questions.forEach(nq => {
                        if (!qList.some(x=>x.question===nq.question)) { qList.push({...nq, _id: nextId++}); added++; }
                    });
                    renderCards(); showToast(added + ' new question(s) added!');
                } else { showToast(data.error||'Generation failed', true); }
            } catch(_) { showToast('Network error', true); }
            genBtn.disabled = false;
            genBtn.innerHTML = '<i class="fas fa-wand-magic-sparkles"></i> Generate 10 More';
        });
        actBar.appendChild(genBtn);

        // Add All
        const addAllBtn = document.createElement('button');
        addAllBtn.className = 'qx-btn-addall';
        addAllBtn.innerHTML = '<i class="fas fa-layer-group"></i> Add All to Quiz';
        addAllBtn.addEventListener('click', async () => {
            if (!qList.length) { showToast('No questions', true); return; }
            if (onPage) {
                qList.forEach(q => insertIntoForm(q));
                showToast('All questions inserted!');
                markAllAdded();
            } else {
                const n = storeMany(qList);
                if (!n) { showToast('All already saved', true); return; }
                showToast(n + ' saved — creating quiz…');
                markAllAdded();
                await createQuizAndRedirect(title);
            }
        });
        actBar.appendChild(addAllBtn);
        root.appendChild(actBar);

        function markAllAdded() {
            addAllBtn.innerHTML = '&#10003; All Added'; addAllBtn.disabled = true; addAllBtn.classList.add('added');
            cardsContainer.querySelectorAll('.btn-add-one').forEach(b => {
                b.innerHTML = '&#10003; Added'; b.disabled = true; b.classList.add('added');
            });
        }

        renderCards();
        return root;
    }

    /* ════════════════════════════════════════════════
     *  PUBLIC API
     * ════════════════════════════════════════════════ */
    window.QuizXMCQ = {
        STORAGE_KEY,
        getSavedQuestions: getSaved,
        clearSavedQuestions: clearSaved,
        showToast,

        renderQuizResponse(quizData) {
            if (!quizData || !quizData.questions || !quizData.questions.length) return null;
            return buildQuizPanel(quizData.questions, {
                topic: quizData.topic || '',
                title: quizData.title || 'AI Generated Quiz',
                difficulty: quizData.difficulty || 'Medium',
                question_type: quizData.question_type || 'mcq'
            });
        },

        async generate(prompt, difficulty, questionType) {
            const res = await fetch('/api/generate-mcq', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({ prompt, difficulty: difficulty||'medium', question_type: questionType||'mcq' })
            });
            return res.json();
        }
    };
})();
