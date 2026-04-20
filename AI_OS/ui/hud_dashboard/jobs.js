// YALI Job Engine — HUD Dashboard Frontend
(function () {

  // ── State ──────────────────────────────────────────
  var currentJobs = [];
  var trackerData = [];

  // ── Tab switching (reuse mind-tab pattern) ─────────
  document.querySelectorAll('.job-tab[data-jtab]').forEach(function(btn) {
    btn.addEventListener('click', function() {
      document.querySelectorAll('.job-tab[data-jtab]').forEach(function(b) { b.classList.remove('active'); });
      document.querySelectorAll('.job-tab-content').forEach(function(c) { c.style.display = 'none'; });
      btn.classList.add('active');
      document.getElementById('jtab-' + btn.dataset.jtab).style.display = 'block';
      if (btn.dataset.jtab === 'tracker') loadTracker();
    });
  });

  // ── Search Tab ─────────────────────────────────────
  var searchBtn = document.getElementById('job-search-btn');
  var jobQueryInput = document.getElementById('job-query');
  var jobLocationInput = document.getElementById('job-location');
  var minScoreInput = document.getElementById('job-min-score');

  function searchJobs() {
    var query = jobQueryInput.value.trim();
    if (!query) return;

    document.getElementById('job-results').innerHTML = '<div class="job-loading"><div class="mind-spinner"></div> Searching jobs...</div>';
    document.getElementById('job-stats-bar').style.display = 'none';

    fetch('/jobs/search', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        query: query,
        location: jobLocationInput.value.trim(),
        min_score: parseInt(minScoreInput.value || '60'),
        max_per_source: 10
      })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      currentJobs = data.jobs || [];
      renderJobResults(currentJobs);
      renderJobStats(data.total, query);
    })
    .catch(function(e) {
      document.getElementById('job-results').innerHTML = '<div class="job-error">Error: ' + e.message + '</div>';
    });
  }

  function renderJobResults(jobs) {
    var container = document.getElementById('job-results');
    if (!jobs.length) {
      container.innerHTML = '<div class="job-empty">No jobs found above score threshold. Lower min score or broaden query.</div>';
      return;
    }
    container.innerHTML = '';
    jobs.forEach(function(job, i) {
      var score = job.match_score || 0;
      var scoreClass = score >= 80 ? 'score-high' : score >= 65 ? 'score-mid' : 'score-low';
      var card = document.createElement('div');
      card.className = 'job-card';
      card.innerHTML =
        '<div class="job-card-top">' +
          '<div class="job-title">' + esc(job.title) + '</div>' +
          '<div class="job-score ' + scoreClass + '">' + score + '%</div>' +
        '</div>' +
        '<div class="job-meta">' + esc(job.company) + ' &bull; ' + esc(job.location) + ' &bull; <span class="job-source">' + esc(job.source) + '</span></div>' +
        '<div class="job-skills">' + renderMatchedSkills(job.score_details) + '</div>' +
        '<div class="job-actions">' +
          '<button class="job-btn job-btn-apply" data-idx="' + i + '">Apply</button>' +
          '<button class="job-btn job-btn-tailor" data-idx="' + i + '">Tailor Resume</button>' +
          '<a class="job-btn job-btn-view" href="' + esc(job.apply_url) + '" target="_blank">View</a>' +
        '</div>';
      container.appendChild(card);
    });

    container.querySelectorAll('.job-btn-apply').forEach(function(btn) {
      btn.addEventListener('click', function() { applyToJob(parseInt(btn.dataset.idx)); });
    });
    container.querySelectorAll('.job-btn-tailor').forEach(function(btn) {
      btn.addEventListener('click', function() { tailorForJob(parseInt(btn.dataset.idx)); });
    });
  }

  function renderMatchedSkills(details) {
    if (!details || !details.matched_skills) return '';
    var skills = details.matched_skills.slice(0, 6);
    return skills.map(function(s) {
      return '<span class="skill-tag matched">' + esc(s) + '</span>';
    }).join('') +
    (details.missing_skills || []).slice(0, 3).map(function(s) {
      return '<span class="skill-tag missing">' + esc(s) + '</span>';
    }).join('');
  }

  function renderJobStats(total, query) {
    var bar = document.getElementById('job-stats-bar');
    bar.style.display = 'flex';
    document.getElementById('job-stats-text').textContent =
      total + ' jobs matched for "' + query + '"';
  }

  function applyToJob(idx) {
    var job = currentJobs[idx];
    if (!job) return;
    document.getElementById('job-results').querySelectorAll('.job-card')[idx]
      .querySelector('.job-btn-apply').textContent = 'Applying...';

    fetch('/jobs/apply', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({job: job})
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var statusText = data.status === 'applied' ? 'Applied!' :
                       data.status === 'skipped' ? 'Creds needed' : data.status;
      document.getElementById('job-results').querySelectorAll('.job-card')[idx]
        .querySelector('.job-btn-apply').textContent = statusText;
      showJobNotif(job.company + ': ' + (data.message || data.status));
    });
  }

  function tailorForJob(idx) {
    var job = currentJobs[idx];
    if (!job) return;
    var btn = document.getElementById('job-results').querySelectorAll('.job-card')[idx]
      .querySelector('.job-btn-tailor');
    btn.textContent = 'Tailoring...';

    fetch('/jobs/tailor', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        jd_text: job.jd_text || job.title + ' at ' + job.company,
        company: job.company,
        role: job.title
      })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      btn.textContent = 'Tailored!';
      showTailorModal(data);
    });
  }

  function showTailorModal(data) {
    var existing = document.getElementById('tailor-modal');
    if (existing) existing.remove();

    var modal = document.createElement('div');
    modal.id = 'tailor-modal';
    modal.className = 'tailor-modal';
    modal.innerHTML =
      '<div class="tailor-modal-inner">' +
        '<div class="tailor-modal-header">' +
          '<span>Tailored for ' + esc(data.role || '') + ' @ ' + esc(data.company || '') + '</span>' +
          '<button id="tailor-close" class="mind-tab">x</button>' +
        '</div>' +
        '<div class="tailor-section-label">TAILORED SUMMARY</div>' +
        '<div class="tailor-content">' + esc(data.summary || '') + '</div>' +
        '<div class="tailor-section-label">SKILLS TO HIGHLIGHT</div>' +
        '<div class="tailor-content">' + (data.skills_to_highlight || []).map(function(s) {
          return '<span class="kw-tag">' + esc(s) + '</span>';
        }).join('') + '</div>' +
        '<div class="tailor-section-label">COVER LETTER</div>' +
        '<div class="tailor-content tailor-cover">' + esc(data.cover_letter || '').replace(/\n/g, '<br>') + '</div>' +
        (data.resume_pdf_path ? '<div class="tailor-paths">Resume PDF: ' + esc(data.resume_pdf_path) + '</div>' : '') +
      '</div>';

    document.body.appendChild(modal);
    document.getElementById('tailor-close').addEventListener('click', function() { modal.remove(); });
  }

  // ── Tracker Tab ────────────────────────────────────
  function loadTracker() {
    fetch('/jobs/tracker')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      trackerData = data.applications || [];
      renderTrackerStats(data.stats || {});
      renderTrackerTable(trackerData);
    });
  }

  function renderTrackerStats(stats) {
    document.getElementById('tracker-total').textContent = stats.total || 0;
    document.getElementById('tracker-interview').textContent =
      (stats.by_status || {}).interview || 0;
    document.getElementById('tracker-offer').textContent =
      (stats.by_status || {}).offer || 0;
    document.getElementById('tracker-rate').textContent =
      (stats.interview_rate || 0) + '%';
  }

  function renderTrackerTable(apps) {
    var tbody = document.getElementById('tracker-tbody');
    tbody.innerHTML = '';
    if (!apps.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="tracker-empty">No applications yet.</td></tr>';
      return;
    }
    apps.forEach(function(app) {
      var tr = document.createElement('tr');
      tr.innerHTML =
        '<td class="tracker-company">' + esc(app.company) + '</td>' +
        '<td>' + esc(app.title) + '</td>' +
        '<td><span class="status-badge status-' + app.status + '">' + esc(app.status) + '</span></td>' +
        '<td>' + esc(app.applied_date || '') + '</td>' +
        '<td>' +
          '<select class="status-select" data-id="' + esc(app.job_id) + '">' +
          ['applied','viewed','phone_screen','interview','offer','rejected'].map(function(s) {
            return '<option value="' + s + '"' + (s === app.status ? ' selected' : '') + '>' + s + '</option>';
          }).join('') +
          '</select>' +
        '</td>';
      tbody.appendChild(tr);
    });

    tbody.querySelectorAll('.status-select').forEach(function(sel) {
      sel.addEventListener('change', function() {
        fetch('/jobs/tracker/' + sel.dataset.id, {
          method: 'PATCH',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({status: sel.value})
        }).then(function() { loadTracker(); });
      });
    });
  }

  var trackerSearchInput = document.getElementById('tracker-search');
  if (trackerSearchInput) {
    trackerSearchInput.addEventListener('input', function() {
      var q = this.value.toLowerCase();
      var filtered = trackerData.filter(function(a) {
        return a.company.toLowerCase().includes(q) || a.title.toLowerCase().includes(q);
      });
      renderTrackerTable(filtered);
    });
  }

  // ── Follow-up Tab ──────────────────────────────────
  var followupRunBtn = document.getElementById('followup-run-btn');
  if (followupRunBtn) {
    followupRunBtn.addEventListener('click', function() {
      var dryRun = document.getElementById('followup-dryrun').checked;
      followupRunBtn.textContent = 'Checking...';
      fetch('/jobs/followup', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({dry_run: dryRun})
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        followupRunBtn.textContent = 'Run Follow-up Check';
        renderFollowupResults(data.followups || []);
      });
    });
  }

  function renderFollowupResults(results) {
    var container = document.getElementById('followup-results');
    container.innerHTML = '';
    if (!results.length) {
      container.innerHTML = '<div class="job-empty">No pending follow-ups.</div>';
      return;
    }
    results.forEach(function(r) {
      var div = document.createElement('div');
      div.className = 'followup-card';
      div.innerHTML =
        '<div class="followup-company">' + esc(r.company) + ' — ' + esc(r.role) + '</div>' +
        '<pre class="followup-draft">' + esc(r.email_draft) + '</pre>';
      container.appendChild(div);
    });
  }

  // ── Helpers ────────────────────────────────────────
  function esc(str) {
    return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function showJobNotif(msg) {
    var n = document.getElementById('job-notif');
    if (!n) return;
    n.textContent = msg;
    n.style.display = 'block';
    setTimeout(function() { n.style.display = 'none'; }, 4000);
  }

  if (searchBtn) searchBtn.addEventListener('click', searchJobs);
  if (jobQueryInput) {
    jobQueryInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') searchJobs();
    });
  }

})();
