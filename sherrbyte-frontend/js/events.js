/* ── SherrByte Event Tracker ──────────────────────────────────────────────
   Batches interaction events and flushes to /v1/interactions every 5s.
   Tracks: impressions, opens, dwell time, scroll %, saves, shares, hides.
────────────────────────────────────────────────────────────────────────── */

const Tracker = (() => {
  const BASE      = window.location.hostname === 'localhost'
    ? 'http://localhost:8000' : 'https://sherrbyte-api.fly.dev';
  const FLUSH_MS  = 5000;
  const MAX_BATCH = 50;

  let _queue  = [];
  let _timer  = null;
  let _dwell  = {};   // articleId → { start: ms, scrollMax: 0 }

  function _push(event) {
    if (!API.isLoggedIn()) return;
    _queue.push({ ...event, interacted_at: new Date().toISOString() });
    if (_queue.length >= MAX_BATCH) _flush();
    else if (!_timer) _timer = setTimeout(_flush, FLUSH_MS);
  }

  async function _flush() {
    clearTimeout(_timer); _timer = null;
    if (!_queue.length || !API.isLoggedIn()) return;
    const batch = _queue.splice(0, MAX_BATCH);
    try {
      const token = localStorage.getItem('sb_access');
      if (!token) return;
      await fetch(`${BASE}/v1/interactions`, {
        method: 'POST',
        headers: {
          'Content-Type':  'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ events: batch }),
      });
    } catch { /* silent — events lost but app works fine */ }
  }

  // Public API
  function impression(articleId)         { _push({ article_id: articleId, event_type: 'impression' }); }
  function open(articleId, sourceId)     { _push({ article_id: articleId, event_type: 'open', source_id: sourceId }); }
  function save(articleId)               { _push({ article_id: articleId, event_type: 'save' }); }
  function share(articleId)              { _push({ article_id: articleId, event_type: 'share' }); }
  function hide(articleId)               { _push({ article_id: articleId, event_type: 'hide' }); }
  function skip(articleId)               { _push({ article_id: articleId, event_type: 'skip' }); }
  function muteSource(articleId, srcId)  { _push({ article_id: articleId, event_type: 'mute_source', source_id: srcId }); }

  function startDwell(articleId) {
    _dwell[articleId] = { start: Date.now(), scrollMax: 0 };
  }

  function updateScroll(articleId, pct) {
    if (_dwell[articleId]) _dwell[articleId].scrollMax = Math.max(_dwell[articleId].scrollMax, pct);
  }

  function endDwell(articleId) {
    const d = _dwell[articleId];
    if (!d) return;
    const ms = Date.now() - d.start;
    delete _dwell[articleId];
    if (ms > 3000) {   // only count reads > 3 seconds
      _push({
        article_id: articleId, event_type: 'dwell',
        dwell_ms: ms, scroll_pct: d.scrollMax,
      });
    }
  }

  // Flush on page hide (mobile background)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') _flush();
  });
  window.addEventListener('pagehide', _flush);

  return { impression, open, save, share, hide, skip, muteSource, startDwell, updateScroll, endDwell, flush: _flush };
})();
