/* YALI Finance Panel — ticker, brief, predict, history */

const MARKET_OPEN_HOUR = 9;
const MARKET_CLOSE_HOUR = 15;
const MARKET_CLOSE_MIN = 30;

function isMarketHours() {
  const now = new Date();
  const h = now.getHours(), m = now.getMinutes();
  return h > MARKET_OPEN_HOUR || (h === MARKET_OPEN_HOUR && m >= 15)
      && (h < MARKET_CLOSE_HOUR || (h === MARKET_CLOSE_HOUR && m <= MARKET_CLOSE_MIN));
}

// ── Ticker ─────────────────────────────────────────────────────────────────

function updateTickerUI(data) {
  const pairs = [
    { key: 'nifty',     pId: 't-nifty-price',  cId: 't-nifty-chg'  },
    { key: 'sensex',    pId: 't-sensex-price', cId: 't-sensex-chg' },
    { key: 'banknifty', pId: 't-bnk-price',    cId: 't-bnk-chg'    },
  ];
  pairs.forEach(({ key, pId, cId }) => {
    const d = data[key];
    if (!d || d.error) return;
    const pEl = document.getElementById(pId);
    const cEl = document.getElementById(cId);
    if (pEl) pEl.textContent = `₹${d.price.toLocaleString('en-IN')}`;
    if (cEl) {
      const sign = d.change_pct >= 0 ? '+' : '';
      cEl.textContent = `${sign}${d.change_pct}%`;
      cEl.className = 'ticker-change ' + (d.change_pct >= 0 ? 'up' : 'down');
    }
  });
  const asOf = document.getElementById('ticker-as-of');
  if (asOf && data.as_of) asOf.textContent = `as of ${data.as_of}`;
}

async function fetchTicker() {
  try {
    const res = await fetch('/finance/overview');
    const data = await res.json();
    updateTickerUI(data);
  } catch (e) {
    console.warn('Ticker fetch failed:', e);
  }
}

// ── News Feed ──────────────────────────────────────────────────────────────

async function fetchNews() {
  try {
    const res = await fetch('/finance/news?n=4');
    const data = await res.json();
    const feed = document.getElementById('finance-news-feed');
    if (!feed) return;
    feed.innerHTML = data.news.map(n => `
      <div class="news-item">
        <span class="news-title">${n.title}</span>
        <span class="news-meta">${n.source} · ${n.published}</span>
      </div>`).join('');
  } catch (e) {}
}

// ── Brief ──────────────────────────────────────────────────────────────────

async function fetchBrief() {
  const loading = document.getElementById('finance-brief-loading');
  const box = document.getElementById('finance-brief-box');
  const text = document.getElementById('finance-brief-text');
  const ts = document.getElementById('finance-brief-ts');

  loading.style.display = 'flex';
  box.style.display = 'none';

  try {
    const res = await fetch('/finance/brief', { method: 'POST' });
    const data = await res.json();
    text.textContent = data.brief || 'Brief unavailable.';
    ts.textContent = `Generated: ${new Date().toLocaleTimeString()}`;
    box.style.display = 'block';
  } catch (e) {
    text.textContent = 'Error fetching brief.';
    box.style.display = 'block';
  } finally {
    loading.style.display = 'none';
  }
}

// ── Predict ────────────────────────────────────────────────────────────────

async function runPredict() {
  const input = document.getElementById('finance-predict-input');
  const question = input.value.trim();
  if (!question) return;

  const loading = document.getElementById('finance-predict-loading');
  const result = document.getElementById('finance-predict-result');
  const dirEl = document.getElementById('predict-direction');
  const textEl = document.getElementById('predict-text');

  loading.style.display = 'flex';
  result.style.display = 'none';

  try {
    const res = await fetch('/finance/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    const pred = data.prediction || 'Prediction unavailable.';

    // detect direction for badge
    const lower = pred.toLowerCase();
    let dir = 'NEUTRAL', dirClass = 'dir-neutral';
    if (lower.includes('bullish') || lower.includes('rise') || lower.includes('upward')) {
      dir = 'BULLISH ▲'; dirClass = 'dir-bullish';
    } else if (lower.includes('bearish') || lower.includes('fall') || lower.includes('downward')) {
      dir = 'BEARISH ▼'; dirClass = 'dir-bearish';
    }

    dirEl.textContent = dir;
    dirEl.className = 'predict-direction ' + dirClass;
    textEl.textContent = pred;
    result.style.display = 'block';
  } catch (e) {
    textEl.textContent = 'Simulation failed.';
    result.style.display = 'block';
  } finally {
    loading.style.display = 'none';
  }
}

// ── Prediction History ─────────────────────────────────────────────────────

async function loadHistory() {
  const container = document.getElementById('prediction-history');
  container.innerHTML = '<div class="finance-loading-inline">Loading...</div>';
  try {
    const res = await fetch('/finance/predictions');
    const data = await res.json();
    const preds = data.predictions || [];
    if (!preds.length) {
      container.innerHTML = '<div class="history-empty">No predictions yet. Use Predict tab.</div>';
      return;
    }
    container.innerHTML = preds.map(p => {
      const dirClass = p.direction === 'bullish' ? 'dir-bullish' : p.direction === 'bearish' ? 'dir-bearish' : 'dir-neutral';
      const outcomeClass = p.outcome === 'correct' ? 'outcome-correct' : p.outcome === 'wrong' ? 'outcome-wrong' : 'outcome-pending';
      return `
        <div class="history-card">
          <div class="history-meta">
            <span class="history-date">${p.date}</span>
            <span class="predict-direction ${dirClass}" style="font-size:11px;padding:2px 8px">${p.direction.toUpperCase()}</span>
            <span class="history-conf">${p.confidence}%</span>
            <span class="history-outcome ${outcomeClass}">${p.outcome}</span>
          </div>
          <div class="history-question">${p.question}</div>
        </div>`;
    }).join('');
  } catch (e) {
    container.innerHTML = '<div class="history-empty">Failed to load history.</div>';
  }
}

// ── Tab switching ──────────────────────────────────────────────────────────

function initFinanceTabs() {
  document.querySelectorAll('.finance-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.finance-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const tab = btn.dataset.ftab;
      document.querySelectorAll('.finance-tab-content').forEach(c => c.style.display = 'none');
      const el = document.getElementById(`ftab-${tab}`);
      if (el) el.style.display = 'block';
    });
  });
}

// ── WebSocket ticker integration ───────────────────────────────────────────

function hookTickerToWS() {
  // piggyback on existing WS in app.js — listen for type=ticker
  const _origOnMsg = window._yaliWSOnMessage;
  window._yaliFinanceWSHook = function(data) {
    if (data.type === 'ticker') updateTickerUI(data.data);
  };
}

// ── Init ───────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initFinanceTabs();

  // Ticker: load immediately, then every 5 min
  fetchTicker();
  setInterval(fetchTicker, 5 * 60 * 1000);

  // News on load
  fetchNews();

  // Buttons
  const briefBtn = document.getElementById('finance-brief-btn');
  if (briefBtn) briefBtn.addEventListener('click', fetchBrief);

  const predictBtn = document.getElementById('finance-predict-btn');
  if (predictBtn) predictBtn.addEventListener('click', runPredict);

  const predictInput = document.getElementById('finance-predict-input');
  if (predictInput) predictInput.addEventListener('keydown', e => { if (e.key === 'Enter') runPredict(); });

  const historyBtn = document.getElementById('finance-history-btn');
  if (historyBtn) historyBtn.addEventListener('click', loadHistory);

  const refreshBtn = document.getElementById('ticker-refresh-btn');
  if (refreshBtn) refreshBtn.addEventListener('click', fetchTicker);

  hookTickerToWS();
});
