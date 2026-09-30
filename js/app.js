/**
 * CAT Exam PYQ Master Hub - Frontend Application Engine
 * Supports Practice Mode, Full Timed Mock Exam Mode, Dynamic Filters,
 * MathJax LaTeX rendering, Zoomable Diagrams, LocalStorage Persistence.
 */

(function () {
  'use strict';

  // --- STATE ---
  const state = {
    allQuestions: [],
    filteredQuestions: [],
    currentSection: 'ALL', // 'ALL' | 'VARC' | 'DILR' | 'QA'
    currentYear: 'ALL',    // 'ALL' | 2024..2017
    currentSlot: 'ALL',    // 'ALL' | 1 | 2 | 3
    currentType: 'ALL',    // 'ALL' | 'MCQ' | 'TITA'
    currentStatus: 'ALL',  // 'ALL' | 'UNATTEMPTED' | 'CORRECT' | 'INCORRECT' | 'BOOKMARKED'
    searchQuery: '',
    currentPage: 1,
    pageSize: 15,
    mode: 'practice', // 'practice' | 'exam'
    
    // User progress in Practice Mode
    responses: {}, // { [qId]: { selected: 'A'|string, isCorrect: bool, checked: bool } }
    bookmarks: new Set(),
    
    // Exam Mode State
    exam: {
      active: false,
      section: 'QA',
      questions: [],
      currentIndex: 0,
      responses: {}, // { [qId]: { selected: string, status: 'answered'|'review'|'not_answered' } }
      timeRemaining: 40 * 60, // 40 minutes (CAT standard)
      timerInterval: null,
      submitted: false,
      result: null
    }
  };

  // --- DOM ELEMENTS ---
  const el = {
    themeBtn: document.getElementById('themeToggleBtn'),
    secTabs: document.querySelectorAll('.sec-tab'),
    modePracticeBtn: document.getElementById('modePracticeBtn'),
    modeExamBtn: document.getElementById('modeExamBtn'),
    yearChips: document.getElementById('yearChips'),
    slotChips: document.getElementById('slotChips'),
    typeChips: document.getElementById('typeChips'),
    statusChips: document.getElementById('statusChips'),
    searchInput: document.getElementById('searchInput'),
    shuffleBtn: document.getElementById('shuffleBtn'),
    resetFiltersBtn: document.getElementById('resetFiltersBtn'),
    questionsContainer: document.getElementById('questionsContainer'),
    paginationContainer: document.getElementById('paginationContainer'),
    statTotal: document.getElementById('statTotal'),
    statAttempted: document.getElementById('statAttempted'),
    statAccuracy: document.getElementById('statAccuracy'),
    statBookmarks: document.getElementById('statBookmarks'),
    quickCountInfo: document.getElementById('quickCountInfo'),
    
    // Exam Elements
    examSidebar: document.getElementById('examSidebar'),
    examTimer: document.getElementById('examTimer'),
    examPalette: document.getElementById('examPalette'),
    examPrevBtn: document.getElementById('examPrevBtn'),
    examNextBtn: document.getElementById('examNextBtn'),
    examReviewBtn: document.getElementById('examReviewBtn'),
    examClearBtn: document.getElementById('examClearBtn'),
    examSubmitBtn: document.getElementById('examSubmitBtn'),
    
    // Modals
    imageModal: document.getElementById('imageModal'),
    modalImage: document.getElementById('modalImage'),
    modalCloseBtn: document.getElementById('modalCloseBtn'),
    scoreModal: document.getElementById('scoreModal'),
    scoreModalCloseBtn: document.getElementById('scoreModalCloseBtn')
  };

  // --- INITIALIZATION ---
  function init() {
    loadSavedData();
    initTheme();
    setupEventListeners();
    loadQuestions();
  }

  // --- LOCAL STORAGE ---
  function loadSavedData() {
    try {
      const savedResp = localStorage.getItem('cat_pyq_responses');
      if (savedResp) state.responses = JSON.parse(savedResp);

      const savedBm = localStorage.getItem('cat_pyq_bookmarks');
      if (savedBm) state.bookmarks = new Set(JSON.parse(savedBm));
    } catch (e) {
      console.warn('LocalStorage load error:', e);
    }
  }

  function saveResponses() {
    try {
      localStorage.setItem('cat_pyq_responses', JSON.stringify(state.responses));
    } catch (e) {}
  }

  function saveBookmarks() {
    try {
      localStorage.setItem('cat_pyq_bookmarks', JSON.stringify(Array.from(state.bookmarks)));
    } catch (e) {}
  }

  // --- THEME ---
  function initTheme() {
    const savedTheme = localStorage.getItem('cat_pyq_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
  }

  function toggleTheme() {
    const curr = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = curr === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('cat_pyq_theme', next);
    updateThemeIcon(next);
  }

  function updateThemeIcon(t) {
    if (!el.themeBtn) return;
    el.themeBtn.innerHTML = t === 'dark' ? '☀️' : '🌙';
    el.themeBtn.title = t === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode';
  }

  // --- DATA LOADING ---
  function loadQuestions() {
    // Check if loaded via cat_data.js script
    if (window.CAT_DATA && Array.isArray(window.CAT_DATA) && window.CAT_DATA.length > 0) {
      processQuestionsData(window.CAT_DATA);
      return;
    }

    // Otherwise fetch data/cat_pyqs.json
    fetch('data/cat_pyqs.json')
      .then(r => {
        if (!r.ok) throw new Error('Network error loading data');
        return r.json();
      })
      .then(data => {
        processQuestionsData(data);
      })
      .catch(err => {
        console.error('Fetch error:', err);
        el.questionsContainer.innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">⚠️</div>
            <h3>Unable to Load Questions</h3>
            <p>Please ensure you are running a local web server (e.g. <code>python -m http.server</code>) or that <code>data/cat_data.js</code> exists.</p>
          </div>
        `;
      });
  }

  function processQuestionsData(data) {
    state.allQuestions = data;
    renderYearChips();
    applyFilters();
    updateStats();
  }

  // --- CHIP GENERATION ---
  function renderYearChips() {
    if (!el.yearChips) return;
    const years = Array.from(new Set(state.allQuestions.map(q => q.year))).sort((a, b) => b - a);
    let html = `<button class="chip ${state.currentYear === 'ALL' ? 'active' : ''}" data-year="ALL">All Years</button>`;
    years.forEach(yr => {
      html += `<button class="chip ${state.currentYear == yr ? 'active' : ''}" data-year="${yr}">CAT ${yr}</button>`;
    });
    el.yearChips.innerHTML = html;

    // Attach click listener
    el.yearChips.querySelectorAll('.chip').forEach(btn => {
      btn.addEventListener('click', () => {
        el.yearChips.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        state.currentYear = btn.dataset.year;
        state.currentPage = 1;
        applyFilters();
      });
    });
  }

  // --- FILTERING ---
  function applyFilters() {
    if (state.mode === 'exam' && state.exam.active) {
      renderExamQuestion();
      return;
    }

    let list = state.allQuestions;

    // Section Filter
    if (state.currentSection !== 'ALL') {
      list = list.filter(q => q.section === state.currentSection);
    }

    // Year Filter
    if (state.currentYear !== 'ALL') {
      list = list.filter(q => q.year == state.currentYear);
    }

    // Slot Filter
    if (state.currentSlot !== 'ALL') {
      list = list.filter(q => q.slot == state.currentSlot);
    }

    // Type Filter
    if (state.currentType !== 'ALL') {
      list = list.filter(q => q.type === state.currentType);
    }

    // Status Filter
    if (state.currentStatus === 'BOOKMARKED') {
      list = list.filter(q => state.bookmarks.has(q.id));
    } else if (state.currentStatus === 'UNATTEMPTED') {
      list = list.filter(q => !state.responses[q.id]?.checked);
    } else if (state.currentStatus === 'CORRECT') {
      list = list.filter(q => state.responses[q.id]?.isCorrect === true);
    } else if (state.currentStatus === 'INCORRECT') {
      list = list.filter(q => state.responses[q.id]?.checked && state.responses[q.id]?.isCorrect === false);
    }

    // Live Keyword Search
    if (state.searchQuery.trim()) {
      const qLower = state.searchQuery.trim().toLowerCase();
      list = list.filter(q => {
        return (
          q.questionText.toLowerCase().includes(qLower) ||
          q.header.toLowerCase().includes(qLower) ||
          (q.passageHtml && q.passageHtml.toLowerCase().includes(qLower)) ||
          q.choices.some(c => c.text.toLowerCase().includes(qLower))
        );
      });
    }

    state.filteredQuestions = list;
    renderQuestionsList();
    renderPagination();
    updateStats();
  }

  // --- RENDER PRACTICE QUESTIONS ---
  function renderQuestionsList() {
    const container = el.questionsContainer;
    if (!container) return;

    if (state.filteredQuestions.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🔍</div>
          <h3>No Questions Found</h3>
          <p>Try adjusting your search query or reset the filters to see more PYQs.</p>
          <button class="btn btn-secondary" style="margin-top:1rem" id="emptyResetBtn">Reset All Filters</button>
        </div>
      `;
      const btn = document.getElementById('emptyResetBtn');
      if (btn) btn.onclick = resetAllFilters;
      return;
    }

    const startIndex = (state.currentPage - 1) * state.pageSize;
    const pageItems = state.filteredQuestions.slice(startIndex, startIndex + state.pageSize);

    let html = '';
    pageItems.forEach((q, idx) => {
      const qIndexGlobal = startIndex + idx + 1;
      const resp = state.responses[q.id] || {};
      const isBookmarked = state.bookmarks.has(q.id);

      const secBadgeClass = q.section === 'QA' ? 'badge-qa' : q.section === 'DILR' ? 'badge-dilr' : 'badge-varc';

      html += `
        <div class="question-card" id="q_card_${q.id}" data-id="${q.id}" data-sec="${q.section}">
          <!-- Card Header Bar -->
          <div class="card-header-bar">
            <div class="card-badges-left">
              <span class="badge ${secBadgeClass}">${q.section === 'QA' ? 'Quant / QA' : q.section}</span>
              <span class="badge badge-year">CAT ${q.year} • Slot ${q.slot}</span>
              <span class="badge badge-year">Q${q.qNo}</span>
              <span class="badge ${q.type === 'TITA' ? 'badge-tita' : 'badge-type'}">${q.type}</span>
            </div>
            <div class="card-actions-right">
              <button class="btn-card-tool ${isBookmarked ? 'bookmarked' : ''}" data-action="bookmark" data-id="${q.id}" title="${isBookmarked ? 'Remove Bookmark' : 'Bookmark Question'}">
                ${isBookmarked ? '★' : '☆'}
              </button>
            </div>
          </div>

          <!-- Passage / Case Container (if exists) -->
          ${q.passageHtml ? `
            <div class="passage-container">
              <div class="passage-header">
                <span class="passage-title">📖 Reading Passage / Case Set</span>
              </div>
              <div class="passage-body">
                ${q.passageHtml}
              </div>
            </div>
          ` : ''}

          <!-- Question Body -->
          <div class="question-statement">
            ${q.questionHtml}
          </div>

          <!-- Options or TITA -->
          ${q.type === 'MCQ' ? `
            <div class="options-grid ${q.choices.length <= 4 && q.choices.every(c => c.text.length < 40) ? 'two-col' : ''}">
              ${q.choices.map(c => {
                let optClass = 'option-item';
                if (resp.selected === c.key) optClass += ' selected';
                if (resp.checked) {
                  if (q.correctLetter === c.key) {
                    optClass += ' is-correct';
                  } else if (resp.selected === c.key) {
                    optClass += ' is-wrong';
                  }
                }
                return `
                  <div class="${optClass}" data-key="${c.key}" data-qid="${q.id}">
                    <div class="option-key">${c.key}</div>
                    <div class="option-text">${c.html || c.text}</div>
                  </div>
                `;
              }).join('')}
            </div>
          ` : `
            <div class="tita-box">
              <div class="tita-header">⌨️ Type In The Answer (TITA / Non-MCQ)</div>
              <div class="tita-input-wrapper">
                <input type="text" class="tita-input" id="tita_${q.id}" placeholder="Enter answer..." 
                  value="${resp.selected || ''}" ${resp.checked ? 'disabled' : ''} />
              </div>
            </div>
          `}

          <!-- Footer Controls -->
          <div class="card-footer-controls">
            <div class="controls-left">
              ${!resp.checked ? `
                <button class="btn btn-primary" data-action="check" data-id="${q.id}">
                  ✓ Check Answer
                </button>
              ` : `
                <button class="btn btn-secondary" data-action="reset" data-id="${q.id}">
                  ↺ Try Again
                </button>
              `}
              <button class="btn btn-outline-purple" data-action="toggle-exp" data-id="${q.id}">
                💡 ${resp.checked ? 'Hide Solution' : 'View Explanation'}
              </button>
            </div>
            <div class="controls-right">
              ${resp.checked ? (
                resp.isCorrect ? `
                  <span class="correct-ans-callout" style="color:var(--success)">
                    ✓ Correct (+3)
                  </span>
                ` : `
                  <span class="correct-ans-callout" style="color:var(--danger)">
                    ✗ Incorrect (${q.type === 'MCQ' ? '-1' : '0'})
                  </span>
                `
              ) : ''}
            </div>
          </div>

          <!-- Explanation Box (revealed when checked or toggled) -->
          <div class="solution-box" id="sol_${q.id}" style="display: ${resp.showExp || resp.checked ? 'block' : 'none'};">
            <div class="solution-header">
              <div class="correct-ans-callout">
                <span>🎯 Official Answer:</span>
                <strong>${q.answerRaw || (q.correctLetter ? `Choice ${q.correctLetter}` : 'Refer solution')}</strong>
              </div>
              ${q.subpageUrl ? `
                <a href="${q.subpageUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" style="font-size:0.75rem;padding:0.25rem 0.6rem">
                  🔗 2IIM Page
                </a>
              ` : ''}
            </div>

            <!-- Explanatory Text -->
            ${q.explanationHtml ? `
              <div class="solution-body">
                ${q.explanationHtml}
              </div>
            ` : `
              <div class="solution-body">
                <p>Detailed step-by-step explanatory notes available on 2IIM official portal.</p>
              </div>
            `}

            <!-- YouTube Video Solution Embed -->
            ${q.videoUrl ? `
              <div class="video-wrapper">
                <iframe src="${q.videoUrl}" title="2IIM CAT Video Solution" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen loading="lazy"></iframe>
              </div>
            ` : ''}
          </div>
        </div>
      `;
    });

    container.innerHTML = html;

    // Attach card event listeners
    attachCardListeners();

    // Trigger MathJax re-render for clean formulas
    renderMathJax();
  }

  function renderMathJax() {
    if (window.MathJax && window.MathJax.typesetPromise) {
      window.MathJax.typesetPromise().catch(err => console.warn('MathJax err:', err));
    }
  }

  // --- CARD INTERACTION LISTENERS ---
  function attachCardListeners() {
    const container = el.questionsContainer;

    // Option Clicks
    container.querySelectorAll('.option-item').forEach(opt => {
      opt.addEventListener('click', () => {
        const qId = opt.dataset.qid;
        const key = opt.dataset.key;
        const resp = state.responses[qId] || {};
        if (resp.checked) return; // already submitted

        resp.selected = key;
        state.responses[qId] = resp;
        saveResponses();

        // Update UI
        const parentCard = document.getElementById(`q_card_${qId}`);
        if (parentCard) {
          parentCard.querySelectorAll('.option-item').forEach(o => o.classList.remove('selected'));
          opt.classList.add('selected');
        }
      });
    });

    // Check Answer Button
    container.querySelectorAll('[data-action="check"]').forEach(btn => {
      btn.addEventListener('click', () => {
        const qId = btn.dataset.id;
        checkAnswer(qId);
      });
    });

    // Try Again Button
    container.querySelectorAll('[data-action="reset"]').forEach(btn => {
      btn.addEventListener('click', () => {
        const qId = btn.dataset.id;
        delete state.responses[qId];
        saveResponses();
        applyFilters();
      });
    });

    // Toggle Explanation Button
    container.querySelectorAll('[data-action="toggle-exp"]').forEach(btn => {
      btn.addEventListener('click', () => {
        const qId = btn.dataset.id;
        const solBox = document.getElementById(`sol_${qId}`);
        if (solBox) {
          const isShown = solBox.style.display !== 'none';
          solBox.style.display = isShown ? 'none' : 'block';
          btn.innerHTML = isShown ? '💡 View Explanation' : '💡 Hide Solution';
          if (!isShown) renderMathJax();
        }
      });
    });

    // Bookmark Button
    container.querySelectorAll('[data-action="bookmark"]').forEach(btn => {
      btn.addEventListener('click', () => {
        const qId = btn.dataset.id;
        if (state.bookmarks.has(qId)) {
          state.bookmarks.delete(qId);
          btn.classList.remove('bookmarked');
          btn.innerHTML = '☆';
          btn.title = 'Bookmark Question';
        } else {
          state.bookmarks.add(qId);
          btn.classList.add('bookmarked');
          btn.innerHTML = '★';
          btn.title = 'Remove Bookmark';
        }
        saveBookmarks();
        updateStats();
      });
    });

    // Image handling & zoom
    container.querySelectorAll('img').forEach(img => {
      // Automatic fallback if local path fails
      img.addEventListener('error', function () {
        if (this.dataset.remoteSrc && this.src !== this.dataset.remoteSrc) {
          console.warn('Image failed to load locally, falling back to remote:', this.dataset.remoteSrc);
          this.src = this.dataset.remoteSrc;
        }
      });

      img.addEventListener('click', () => {
        openImageModal(img.src);
      });
    });
  }

  function showToast(msg) {
    let toast = document.getElementById('appToast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'appToast';
      toast.className = 'toast-notification';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
      toast.classList.remove('show');
    }, 2800);
  }

  function checkAnswer(qId) {
    const q = state.allQuestions.find(item => item.id === qId);
    if (!q) return;

    let userVal = '';
    if (q.type === 'MCQ') {
      userVal = state.responses[qId]?.selected || '';
      if (!userVal) {
        showToast('⚠️ Please select an option before checking!');
        return;
      }
    } else {
      const input = document.getElementById(`tita_${qId}`);
      userVal = input ? input.value.trim() : '';
      if (!userVal) {
        showToast('⚠️ Please enter your answer before checking!');
        return;
      }
    }

    // Determine correctness
    let isCorrect = false;
    if (q.type === 'MCQ') {
      isCorrect = (q.correctLetter && userVal.toUpperCase() === q.correctLetter.toUpperCase());
      if (!isCorrect && q.answerRaw) {
        // Fallback string matching
        const cleanRaw = q.answerRaw.toLowerCase();
        const selectedChoice = q.choices.find(c => c.key === userVal);
        if (selectedChoice && cleanRaw.includes(selectedChoice.text.toLowerCase())) {
          isCorrect = true;
        }
      }
    } else {
      // TITA matching (numbers or text)
      const cleanUser = userVal.replace(/\s+/g, '').toLowerCase();
      const cleanAns = (q.answerRaw || '').replace(/correct answer:?/i, '').replace(/\s+/g, '').toLowerCase();
      isCorrect = (cleanUser === cleanAns || cleanAns.includes(cleanUser));
    }

    state.responses[qId] = {
      selected: userVal,
      isCorrect: isCorrect,
      checked: true,
      showExp: true
    };
    saveResponses();
    applyFilters();
  }

  // --- PAGINATION ---
  function renderPagination() {
    const pContainer = el.paginationContainer;
    if (!pContainer) return;

    const totalPages = Math.ceil(state.filteredQuestions.length / state.pageSize);
    if (totalPages <= 1) {
      pContainer.innerHTML = '';
      return;
    }

    let html = `<div class="pagination-bar">`;
    html += `<button class="btn btn-secondary" ${state.currentPage === 1 ? 'disabled' : ''} id="prevPageBtn">← Previous</button>`;
    html += `<span class="quick-stats-info">Page <strong>${state.currentPage}</strong> of <strong>${totalPages}</strong></span>`;
    html += `<button class="btn btn-secondary" ${state.currentPage === totalPages ? 'disabled' : ''} id="nextPageBtn">Next →</button>`;
    html += `</div>`;

    pContainer.innerHTML = html;

    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');

    if (prevBtn) {
      prevBtn.onclick = () => {
        if (state.currentPage > 1) {
          state.currentPage--;
          renderQuestionsList();
          renderPagination();
          window.scrollTo({ top: 300, behavior: 'smooth' });
        }
      };
    }

    if (nextBtn) {
      nextBtn.onclick = () => {
        if (state.currentPage < totalPages) {
          state.currentPage++;
          renderQuestionsList();
          renderPagination();
          window.scrollTo({ top: 300, behavior: 'smooth' });
        }
      };
    }
  }

  // --- STATS UPDATE ---
  function updateStats() {
    const total = state.allQuestions.length;
    const attempted = Object.values(state.responses).filter(r => r.checked).length;
    const correct = Object.values(state.responses).filter(r => r.checked && r.isCorrect).length;
    const accuracy = attempted > 0 ? Math.round((correct / attempted) * 100) : 0;
    const bmCount = state.bookmarks.size;

    if (el.statTotal) el.statTotal.textContent = total.toLocaleString();
    if (el.statAttempted) el.statAttempted.textContent = attempted.toLocaleString();
    if (el.statAccuracy) el.statAccuracy.textContent = `${accuracy}%`;
    if (el.statBookmarks) el.statBookmarks.textContent = bmCount.toLocaleString();

    if (el.quickCountInfo) {
      el.quickCountInfo.innerHTML = `Showing <strong>${state.filteredQuestions.length}</strong> questions matching filters`;
    }
  }

  // --- TIMED EXAM / MOCK MODE ---
  function startExamMode() {
    state.mode = 'exam';
    if (el.modePracticeBtn) el.modePracticeBtn.classList.remove('active');
    if (el.modeExamBtn) el.modeExamBtn.classList.add('active');

    // Section for exam
    const sec = state.currentSection === 'ALL' ? 'QA' : state.currentSection;
    state.exam.section = sec;
    
    // Choose questions (e.g. 2022 Slot 1 QA or current filtered set)
    let examQs = state.filteredQuestions;
    if (examQs.length === 0 || examQs.length > 34) {
      // Pick a full official paper (e.g. 2022 Slot 1)
      examQs = state.allQuestions.filter(q => q.year === 2022 && q.slot === 1 && q.section === sec);
      if (examQs.length === 0) examQs = state.allQuestions.filter(q => q.section === sec).slice(0, 22);
    }

    state.exam.active = true;
    state.exam.questions = examQs;
    state.exam.currentIndex = 0;
    state.exam.responses = {};
    state.exam.timeRemaining = 40 * 60; // 40 mins
    state.exam.submitted = false;

    // Start timer
    if (state.exam.timerInterval) clearInterval(state.exam.timerInterval);
    state.exam.timerInterval = setInterval(updateExamTimer, 1000);

    // Show sidebar & adjust layout
    document.querySelector('.main-content-layout')?.classList.add('layout-with-sidebar');
    if (el.examSidebar) el.examSidebar.style.display = 'flex';

    renderExamQuestion();
    renderExamPalette();
  }

  function endExamMode() {
    state.mode = 'practice';
    state.exam.active = false;
    if (state.exam.timerInterval) clearInterval(state.exam.timerInterval);

    if (el.modePracticeBtn) el.modePracticeBtn.classList.add('active');
    if (el.modeExamBtn) el.modeExamBtn.classList.remove('active');

    document.querySelector('.main-content-layout')?.classList.remove('layout-with-sidebar');
    if (el.examSidebar) el.examSidebar.style.display = 'none';

    applyFilters();
  }

  function updateExamTimer() {
    if (!state.exam.active) return;
    state.exam.timeRemaining--;

    if (state.exam.timeRemaining <= 0) {
      clearInterval(state.exam.timerInterval);
      showToast('⏱️ Time is up! Submitting your test automatically.');
      submitExam();
      return;
    }

    const mins = Math.floor(state.exam.timeRemaining / 60);
    const secs = state.exam.timeRemaining % 60;
    if (el.examTimer) {
      el.examTimer.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
      if (state.exam.timeRemaining < 300) {
        el.examTimer.style.color = '#ef4444';
      }
    }
  }

  function renderExamQuestion() {
    const q = state.exam.questions[state.exam.currentIndex];
    if (!q) return;

    const container = el.questionsContainer;
    const resp = state.exam.responses[q.id] || {};

    const secBadgeClass = q.section === 'QA' ? 'badge-qa' : q.section === 'DILR' ? 'badge-dilr' : 'badge-varc';

    container.innerHTML = `
      <div class="question-card" data-sec="${q.section}">
        <div class="card-header-bar">
          <div class="card-badges-left">
            <span class="badge ${secBadgeClass}">Question ${state.exam.currentIndex + 1} of ${state.exam.questions.length}</span>
            <span class="badge badge-year">CAT ${q.year} Slot ${q.slot}</span>
            <span class="badge ${q.type === 'TITA' ? 'badge-tita' : 'badge-type'}">${q.type}</span>
          </div>
          <div class="card-actions-right">
            <span style="font-size:0.8rem;color:var(--text-muted)">Marking: +3 / ${q.type === 'MCQ' ? '-1' : '0'}</span>
          </div>
        </div>

        ${q.passageHtml ? `
          <div class="passage-container">
            <div class="passage-header">
              <span class="passage-title">📖 Reading Passage / Case Set</span>
            </div>
            <div class="passage-body">
              ${q.passageHtml}
            </div>
          </div>
        ` : ''}

        <div class="question-statement">
          ${q.questionHtml}
        </div>

        ${q.type === 'MCQ' ? `
          <div class="options-grid">
            ${q.choices.map(c => `
              <div class="option-item ${resp.selected === c.key ? 'selected' : ''}" data-key="${c.key}">
                <div class="option-key">${c.key}</div>
                <div class="option-text">${c.html || c.text}</div>
              </div>
            `).join('')}
          </div>
        ` : `
          <div class="tita-box">
            <div class="tita-header">⌨️ Type In The Answer (TITA)</div>
            <div class="tita-input-wrapper">
              <input type="text" class="tita-input" id="exam_tita_input" placeholder="Enter answer..." 
                value="${resp.selected || ''}" />
            </div>
          </div>
        `}

        <div class="card-footer-controls">
          <div class="controls-left">
            <button class="btn btn-primary" id="examSaveNextBtn">
              Save & Next →
            </button>
            <button class="btn btn-outline-purple" id="examReviewNextBtn">
              Mark for Review & Next
            </button>
            <button class="btn btn-secondary" id="examClearRespBtn">
              Clear Response
            </button>
          </div>
          <div class="controls-right">
            <button class="btn btn-secondary" id="examPrevBtnCard" ${state.exam.currentIndex === 0 ? 'disabled' : ''}>
              ← Previous
            </button>
          </div>
        </div>
      </div>
    `;

    // Attach exam card events
    container.querySelectorAll('.option-item').forEach(opt => {
      opt.addEventListener('click', () => {
        container.querySelectorAll('.option-item').forEach(o => o.classList.remove('selected'));
        opt.classList.add('selected');
        saveExamOption(q.id, opt.dataset.key);
      });
    });

    const titaInput = document.getElementById('exam_tita_input');
    if (titaInput) {
      titaInput.addEventListener('input', () => {
        saveExamOption(q.id, titaInput.value.trim());
      });
    }

    document.getElementById('examSaveNextBtn')?.addEventListener('click', () => {
      const currentResp = state.exam.responses[q.id];
      if (currentResp && currentResp.selected) {
        currentResp.status = 'answered';
      } else {
        if (!currentResp) state.exam.responses[q.id] = { selected: '', status: 'not_answered' };
      }
      nextExamQuestion();
    });

    document.getElementById('examReviewNextBtn')?.addEventListener('click', () => {
      const currentResp = state.exam.responses[q.id] || { selected: '' };
      currentResp.status = currentResp.selected ? 'answered_review' : 'review';
      state.exam.responses[q.id] = currentResp;
      nextExamQuestion();
    });

    document.getElementById('examClearRespBtn')?.addEventListener('click', () => {
      delete state.exam.responses[q.id];
      renderExamQuestion();
      renderExamPalette();
    });

    document.getElementById('examPrevBtnCard')?.addEventListener('click', () => {
      if (state.exam.currentIndex > 0) {
        state.exam.currentIndex--;
        renderExamQuestion();
        renderExamPalette();
      }
    });

    renderExamPalette();
    renderMathJax();
  }

  function saveExamOption(qId, val) {
    if (!state.exam.responses[qId]) {
      state.exam.responses[qId] = { selected: val, status: 'answered' };
    } else {
      state.exam.responses[qId].selected = val;
      if (state.exam.responses[qId].status === 'review') {
        state.exam.responses[qId].status = 'answered_review';
      } else {
        state.exam.responses[qId].status = 'answered';
      }
    }
    renderExamPalette();
  }

  function nextExamQuestion() {
    if (state.exam.currentIndex < state.exam.questions.length - 1) {
      state.exam.currentIndex++;
      renderExamQuestion();
    } else {
      showToast('ℹ️ You have reached the last question. You can review your answers or click Submit Test.');
      renderExamPalette();
    }
  }

  function renderExamPalette() {
    const palette = el.examPalette;
    if (!palette) return;

    let html = '';
    state.exam.questions.forEach((q, idx) => {
      const resp = state.exam.responses[q.id];
      let statusClass = 'status-not-visited';

      if (resp) {
        if (resp.status === 'answered') statusClass = 'status-answered';
        else if (resp.status === 'review') statusClass = 'status-review';
        else if (resp.status === 'answered_review') statusClass = 'status-answered-review';
        else if (resp.status === 'not_answered') statusClass = 'status-not-answered';
      }

      const isActive = idx === state.exam.currentIndex;

      html += `
        <button class="palette-btn ${statusClass} ${isActive ? 'active' : ''}" data-idx="${idx}">
          ${idx + 1}
        </button>
      `;
    });

    palette.innerHTML = html;

    palette.querySelectorAll('.palette-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        state.exam.currentIndex = parseInt(btn.dataset.idx, 10);
        renderExamQuestion();
      });
    });
  }

  function submitExam() {
    if (state.exam.timerInterval) clearInterval(state.exam.timerInterval);

    // Calculate score
    let score = 0;
    let correct = 0;
    let wrong = 0;
    let unattempted = 0;

    state.exam.questions.forEach(q => {
      const userVal = state.exam.responses[q.id]?.selected;
      if (!userVal) {
        unattempted++;
        return;
      }

      let isCorrect = false;
      if (q.type === 'MCQ') {
        isCorrect = (q.correctLetter && userVal.toUpperCase() === q.correctLetter.toUpperCase());
        if (!isCorrect && q.answerRaw) {
          const selectedChoice = q.choices.find(c => c.key === userVal);
          if (selectedChoice && q.answerRaw.toLowerCase().includes(selectedChoice.text.toLowerCase())) {
            isCorrect = true;
          }
        }
        if (isCorrect) {
          score += 3;
          correct++;
        } else {
          score -= 1;
          wrong++;
        }
      } else {
        // TITA
        const cleanUser = userVal.replace(/\s+/g, '').toLowerCase();
        const cleanAns = (q.answerRaw || '').replace(/correct answer:?/i, '').replace(/\s+/g, '').toLowerCase();
        isCorrect = (cleanUser === cleanAns || cleanAns.includes(cleanUser));
        if (isCorrect) {
          score += 3;
          correct++;
        } else {
          wrong++;
        }
      }
    });

    const accuracy = (correct + wrong) > 0 ? Math.round((correct / (correct + wrong)) * 100) : 0;

    showScoreModal({
      score,
      total: state.exam.questions.length,
      correct,
      wrong,
      unattempted,
      accuracy
    });
  }

  function showScoreModal(data) {
    if (!el.scoreModal) return;
    document.getElementById('modalScoreNum').textContent = data.score;
    document.getElementById('scValAttempted').textContent = `${data.correct + data.wrong}/${data.total}`;
    document.getElementById('scValCorrect').textContent = data.correct;
    document.getElementById('scValWrong').textContent = data.wrong;
    document.getElementById('scValAccuracy').textContent = `${data.accuracy}%`;

    el.scoreModal.classList.add('open');
  }

  // --- MODAL & IMAGE ZOOM ---
  function openImageModal(src) {
    if (!el.imageModal || !el.modalImage) return;
    el.modalImage.src = src;
    el.imageModal.classList.add('open');
  }

  function closeImageModal() {
    if (el.imageModal) el.imageModal.classList.remove('open');
  }

  // --- EVENT LISTENERS ---
  function setupEventListeners() {
    // Theme Toggle
    if (el.themeBtn) el.themeBtn.addEventListener('click', toggleTheme);

    // Section Tabs
    el.secTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        el.secTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        state.currentSection = tab.dataset.sec;
        state.currentPage = 1;
        applyFilters();
      });
    });

    // Mode Switch
    if (el.modePracticeBtn) {
      el.modePracticeBtn.addEventListener('click', () => {
        if (state.mode !== 'practice') endExamMode();
      });
    }

    if (el.modeExamBtn) {
      el.modeExamBtn.addEventListener('click', () => {
        if (state.mode !== 'exam') {
          startExamMode();
        }
      });
    }

    // Slot Chips
    if (el.slotChips) {
      el.slotChips.querySelectorAll('.chip').forEach(btn => {
        btn.addEventListener('click', () => {
          el.slotChips.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
          btn.classList.add('active');
          state.currentSlot = btn.dataset.slot;
          state.currentPage = 1;
          applyFilters();
        });
      });
    }

    // Type Chips
    if (el.typeChips) {
      el.typeChips.querySelectorAll('.chip').forEach(btn => {
        btn.addEventListener('click', () => {
          el.typeChips.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
          btn.classList.add('active');
          state.currentType = btn.dataset.type;
          state.currentPage = 1;
          applyFilters();
        });
      });
    }

    // Status Chips
    if (el.statusChips) {
      el.statusChips.querySelectorAll('.chip').forEach(btn => {
        btn.addEventListener('click', () => {
          el.statusChips.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
          btn.classList.add('active');
          state.currentStatus = btn.dataset.status;
          state.currentPage = 1;
          applyFilters();
        });
      });
    }

    // Search Input (Debounced)
    let searchTimer = null;
    if (el.searchInput) {
      el.searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
          state.searchQuery = e.target.value;
          state.currentPage = 1;
          applyFilters();
        }, 250);
      });
    }

    // Shuffle Button
    if (el.shuffleBtn) {
      el.shuffleBtn.addEventListener('click', () => {
        state.filteredQuestions.sort(() => Math.random() - 0.5);
        state.currentPage = 1;
        renderQuestionsList();
        renderPagination();
      });
    }

    // Reset Filters
    if (el.resetFiltersBtn) el.resetFiltersBtn.addEventListener('click', resetAllFilters);

    // Exam Sidebar Controls
    if (el.examSubmitBtn) {
      el.examSubmitBtn.addEventListener('click', () => {
        submitExam();
      });
    }

    // Image Modal Close
    if (el.modalCloseBtn) el.modalCloseBtn.addEventListener('click', closeImageModal);
    if (el.imageModal) {
      el.imageModal.addEventListener('click', (e) => {
        if (e.target === el.imageModal) closeImageModal();
      });
    }

    // Score Modal Close
    if (el.scoreModalCloseBtn) {
      el.scoreModalCloseBtn.addEventListener('click', () => {
        el.scoreModal.classList.remove('open');
        endExamMode();
      });
    }
  }

  function resetAllFilters() {
    state.currentSection = 'ALL';
    state.currentYear = 'ALL';
    state.currentSlot = 'ALL';
    state.currentType = 'ALL';
    state.currentStatus = 'ALL';
    state.searchQuery = '';
    state.currentPage = 1;

    if (el.searchInput) el.searchInput.value = '';

    el.secTabs.forEach(t => t.classList.toggle('active', t.dataset.sec === 'ALL'));
    el.yearChips?.querySelectorAll('.chip').forEach(c => c.classList.toggle('active', c.dataset.year === 'ALL'));
    el.slotChips?.querySelectorAll('.chip').forEach(c => c.classList.toggle('active', c.dataset.slot === 'ALL'));
    el.typeChips?.querySelectorAll('.chip').forEach(c => c.classList.toggle('active', c.dataset.type === 'ALL'));
    el.statusChips?.querySelectorAll('.chip').forEach(c => c.classList.toggle('active', c.dataset.status === 'ALL'));

    applyFilters();
  }

  // Auto-init on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
