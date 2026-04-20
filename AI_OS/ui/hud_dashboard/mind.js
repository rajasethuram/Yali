// ════════════════════════════════════════════════════
// YALI MIND — Interview Co-Pilot Frontend Logic
// ════════════════════════════════════════════════════

(function () {
  // Tab switching
  document.querySelectorAll('.mind-tab[data-tab]').forEach(function(btn) {
    btn.addEventListener('click', function() {
      document.querySelectorAll('.mind-tab[data-tab]').forEach(function(b) { b.classList.remove('active'); });
      document.querySelectorAll('.mind-tab-content').forEach(function(c) { c.style.display = 'none'; });
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).style.display = 'block';
    });
  });

  // ── Live Assist ──────────────────────────────────────

  var askBtn = document.getElementById('mind-ask-btn');
  var questionInput = document.getElementById('mind-question-input');

  function askMind() {
    var question = questionInput.value.trim();
    if (!question) return;

    document.getElementById('mind-answer-box').style.display = 'none';
    document.getElementById('mind-intent-badge').style.display = 'none';
    document.getElementById('mind-loading').style.display = 'flex';

    fetch('/mind/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
      document.getElementById('mind-loading').style.display = 'none';
      if (data.error) { showMindError(data.error); return; }
      renderMindAnswer(data);
    })
    .catch(function(e) {
      document.getElementById('mind-loading').style.display = 'none';
      showMindError('Network error: ' + e.message);
    });
  }

  function renderMindAnswer(data) {
    var badge = document.getElementById('mind-intent-badge');
    document.getElementById('mind-intent-label').textContent = data.label || data.intent || 'General';
    document.getElementById('mind-framework').textContent = data.framework || '';
    badge.style.display = 'flex';

    document.getElementById('mind-opening').textContent = data.opening || '';

    var bulletsEl = document.getElementById('mind-bullets');
    bulletsEl.innerHTML = '';
    (data.bullets || []).forEach(function(b) {
      var li = document.createElement('li');
      li.textContent = b;
      bulletsEl.appendChild(li);
    });

    document.getElementById('mind-example').textContent = data.example || '';

    var kwEl = document.getElementById('mind-keywords');
    kwEl.innerHTML = '';
    (data.keywords || []).forEach(function(kw) {
      var span = document.createElement('span');
      span.className = 'kw-tag';
      span.textContent = kw;
      kwEl.appendChild(span);
    });

    document.getElementById('mind-answer-box').style.display = 'flex';
  }

  function showMindError(msg) {
    document.getElementById('mind-opening').textContent = msg;
    document.getElementById('mind-bullets').innerHTML = '';
    document.getElementById('mind-example').textContent = '';
    document.getElementById('mind-keywords').innerHTML = '';
    document.getElementById('mind-answer-box').style.display = 'flex';
  }

  if (askBtn) askBtn.addEventListener('click', askMind);
  if (questionInput) {
    questionInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); askMind(); }
    });
  }

  // ── Practice Tab ─────────────────────────────────────

  var practiceQuestions = [];
  var practiceIndex = 0;

  function loadPracticeQuestions() {
    var area = document.getElementById('practice-area').value;
    fetch('/mind/questions?area=' + area + '&count=15')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      practiceQuestions = data.questions || [];
      practiceIndex = 0;
      renderPracticeList();
      showPracticeQuestion();
    });
  }

  function renderPracticeList() {
    var list = document.getElementById('practice-question-list');
    list.innerHTML = '';
    practiceQuestions.forEach(function(q, i) {
      var div = document.createElement('div');
      div.className = 'pq-item';
      div.innerHTML = '<div class="pq-type">' + q.type + '</div><div class="pq-text">' + q.question + '</div>';
      (function(idx) {
        div.addEventListener('click', function() { practiceIndex = idx; showPracticeQuestion(); });
      })(i);
      list.appendChild(div);
    });
  }

  function showPracticeQuestion() {
    if (!practiceQuestions.length) return;
    var q = practiceQuestions[practiceIndex];
    document.getElementById('practice-q-num').textContent = 'Question ' + (practiceIndex + 1) + ' / ' + practiceQuestions.length;
    document.getElementById('practice-q-text').textContent = q.question;
    document.getElementById('practice-q-type').textContent = q.type.toUpperCase();
    document.getElementById('practice-question-box').style.display = 'block';
  }

  var practiceStartBtn = document.getElementById('practice-start-btn');
  if (practiceStartBtn) practiceStartBtn.addEventListener('click', loadPracticeQuestions);

  var practiceGetAnswerBtn = document.getElementById('practice-get-answer-btn');
  if (practiceGetAnswerBtn) {
    practiceGetAnswerBtn.addEventListener('click', function() {
      if (!practiceQuestions.length) return;
      var q = practiceQuestions[practiceIndex].question;
      questionInput.value = q;
      document.querySelector('.mind-tab[data-tab="live"]').click();
      askMind();
    });
  }

  var practiceNextBtn = document.getElementById('practice-next-btn');
  if (practiceNextBtn) {
    practiceNextBtn.addEventListener('click', function() {
      practiceIndex = (practiceIndex + 1) % practiceQuestions.length;
      showPracticeQuestion();
    });
  }

  // ── Review Tab ────────────────────────────────────────

  var reviewAnalyzeBtn = document.getElementById('review-analyze-btn');
  if (reviewAnalyzeBtn) {
    reviewAnalyzeBtn.addEventListener('click', function() {
      var transcript = document.getElementById('review-transcript').value.trim();
      if (!transcript) return;

      fetch('/mind/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript: transcript, duration: 0 })
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        document.getElementById('review-overall').textContent = data.overall_score + '/100';
        document.getElementById('review-confidence').textContent = data.confidence_score;
        document.getElementById('review-pace').textContent = data.pace_score;
        document.getElementById('review-structure').textContent = data.structure_score;

        document.getElementById('review-filler').textContent =
          data.filler_count > 0
            ? 'Filler words detected: ' + data.filler_count
            : 'No filler words detected!';

        var sugg = document.getElementById('review-suggestions');
        sugg.innerHTML = '';
        (data.suggestions || []).forEach(function(s) {
          var li = document.createElement('li');
          li.textContent = s;
          sugg.appendChild(li);
        });

        document.getElementById('review-results').style.display = 'block';
      });
    });
  }

})();
