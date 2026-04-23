/* ── SherrByte Feed Renderer ──────────────────────────────────────────────
   Renders hero cards (Mode A) and trending rows (Mode B).
   Handles infinite scroll, saved articles, and context menus.
────────────────────────────────────────────────────────────────────────── */

const Feed = (() => {
  let _cursor    = null;
  let _loading   = false;
  let _exhausted = false;
  let _pillar    = '';
  let _saved     = new Set(JSON.parse(localStorage.getItem('sb_saved') || '[]'));
  let _hidden    = new Set(JSON.parse(localStorage.getItem('sb_hidden') || '[]'));

  // ── TIME UTILS ──
  function _ago(dateStr) {
    if (!dateStr) return '';
    const diff = (Date.now() - new Date(dateStr)) / 1000;
    if (diff < 60)   return 'Just now';
    if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
    return `${Math.floor(diff/86400)}d ago`;
  }

  function _savePersist() {
    localStorage.setItem('sb_saved',  JSON.stringify([..._saved]));
    localStorage.setItem('sb_hidden', JSON.stringify([..._hidden]));
  }

  // ── CARD BUILDERS ──
  function _heroCard(art, idx) {
    const id       = art.id;
    const title    = art.headline_rewrite || art.title || 'Untitled';
    const summary  = art.cached_summary || art.summary_60w || '';
    const img      = art.image_url || '';
    const source   = art.source?.name || art.source_name || '';
    const time     = _ago(art.published_at);
    const tag      = art.tags?.[0]?.microtopic_name || art.micro_topic || art.category || '';
    const isSaved  = _saved.has(id);

    const card = document.createElement('div');
    card.className = 'card-hero';
    card.dataset.id = id;
    card.style.animationDelay = `${idx * 60}ms`;
    card.innerHTML = `
      ${img ? `<img class="card-hero-img" src="${img}" alt="" loading="lazy" decoding="async">` : ''}
      <div class="card-hero-body">
        <div class="card-meta">
          <span class="card-source">${source}</span>
          ${time ? `<span class="card-dot"></span><span class="card-time">${time}</span>` : ''}
        </div>
        <h2 class="card-title-hero">${title}</h2>
        ${summary ? `<p class="card-summary">${summary}</p>` : ''}
        <div class="card-footer">
          ${tag ? `<span class="card-tag">${tag}</span>` : '<span></span>'}
          <div class="card-actions">
            <button class="card-btn btn-save${isSaved?' saved':''}" data-id="${id}" aria-label="Save">
              <svg width="16" height="16" fill="${isSaved?'currentColor':'none'}" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/></svg>
            </button>
            <button class="card-btn btn-more" data-id="${id}" data-source="${source}" aria-label="More">
              <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>
            </button>
          </div>
        </div>
      </div>
    `;

    // Lazy image fade-in
    const imgEl = card.querySelector('img');
    if (imgEl) {
      imgEl.onload  = () => imgEl.classList.add('loaded');
      imgEl.onerror = () => imgEl.remove();
    }

    // Click → open article
    card.addEventListener('click', e => {
      if (e.target.closest('.card-btn')) return;
      App.openArticle(art);
    });

    // Save button
    card.querySelector('.btn-save').addEventListener('click', e => {
      e.stopPropagation();
      _toggleSave(id, e.currentTarget);
    });

    // More button
    card.querySelector('.btn-more').addEventListener('click', e => {
      e.stopPropagation();
      _showMenu(e.currentTarget, art);
    });

    // Impression tracking
    Tracker.impression(id);

    return card;
  }

  function _rowCard(art, idx) {
    const id      = art.id;
    const title   = art.headline_rewrite || art.title || 'Untitled';
    const img     = art.image_url || '';
    const source  = art.source?.name || art.source_name || '';
    const time    = _ago(art.published_at);
    const trending = art.is_trending;

    const row = document.createElement('div');
    row.className = 'card-row';
    row.dataset.id = id;
    row.style.animationDelay = `${idx * 40}ms`;
    row.innerHTML = `
      <div class="card-row-body">
        ${trending ? '<div class="card-trending-badge">🔴 LIVE</div>' : ''}
        <div class="card-row-meta">
          <span class="card-row-source">${source}</span>
          ${time ? `<span class="card-dot" style="background:var(--text-muted);width:2px;height:2px;border-radius:50%;"></span><span class="card-row-time">${time}</span>` : ''}
        </div>
        <p class="card-row-title">${title}</p>
      </div>
      ${img ? `<img class="card-row-img" src="${img}" alt="" loading="lazy" decoding="async">` : ''}
    `;

    const imgEl = row.querySelector('img');
    if (imgEl) imgEl.onerror = () => imgEl.remove();

    row.addEventListener('click', () => App.openArticle(art));
    Tracker.impression(id);
    return row;
  }

  // ── SAVE TOGGLE ──
  function _toggleSave(id, btn) {
    if (_saved.has(id)) {
      _saved.delete(id);
      btn.classList.remove('saved');
      btn.querySelector('svg').setAttribute('fill','none');
      App.toast('Removed from saved');
      Tracker.skip(id);
    } else {
      _saved.add(id);
      btn.classList.add('saved');
      btn.querySelector('svg').setAttribute('fill','currentColor');
      App.toast('Saved ✓');
      Tracker.save(id);
    }
    _savePersist();
  }

  // ── CONTEXT MENU ──
  function _showMenu(btn, art) {
    document.querySelector('.card-menu')?.remove();
    const menu = document.createElement('div');
    menu.className = 'card-menu';
    menu.style.top = `${btn.getBoundingClientRect().bottom + window.scrollY + 6}px`;
    menu.innerHTML = `
      <button class="menu-item" data-action="hide">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
        Hide this story
      </button>
      <button class="menu-item" data-action="less">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
        Show less like this
      </button>
      <button class="menu-item danger" data-action="mute">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
        Mute ${art.source?.name || art.source_name || 'source'}
      </button>
    `;

    menu.querySelector('[data-action="hide"]').onclick = () => {
      _hideArticle(art.id); menu.remove();
    };
    menu.querySelector('[data-action="less"]').onclick = () => {
      Tracker.skip(art.id); App.toast('Got it — showing less like this'); menu.remove();
    };
    menu.querySelector('[data-action="mute"]').onclick = () => {
      Tracker.muteSource(art.id, art.source?.id || null);
      _hideArticle(art.id); App.toast('Source muted'); menu.remove();
    };

    document.body.appendChild(menu);
    setTimeout(() => document.addEventListener('click', () => menu.remove(), { once: true }), 10);
  }

  function _hideArticle(id) {
    _hidden.add(id); _savePersist();
    document.querySelector(`[data-id="${id}"]`)?.remove();
    Tracker.hide(id);
  }

  // ── RENDER BATCH ──
  function _renderBatch(articles) {
    const list = document.getElementById('feed-list');

    // Split: first 3 hero, rest as rows with a trending label
    const heroes  = articles.slice(0, 3).filter(a => !_hidden.has(a.id));
    const rows    = articles.slice(3).filter(a => !_hidden.has(a.id));

    heroes.forEach((art, i) => list.appendChild(_heroCard(art, i)));

    if (rows.length) {
      const label = document.createElement('div');
      label.className = 'trending-label';
      label.innerHTML = `<span class="trending-label-text">Latest</span><div class="trending-label-line"></div>`;
      list.appendChild(label);
      rows.forEach((art, i) => list.appendChild(_rowCard(art, heroes.length + i)));
    }
  }

  // ── LOAD FEED ──
  async function load(reset = false) {
    if (_loading || _exhausted) return;
    _loading = true;

    if (reset) {
      _cursor    = null;
      _exhausted = false;
      document.getElementById('feed-list').innerHTML = `
        <div class="skeleton-hero"></div>
        <div class="skeleton-hero"></div>
        <div class="skeleton-row"></div>
        <div class="skeleton-row"></div>
      `;
      document.getElementById('feed-end').classList.add('hidden');
    }

    try {
      let data;
      const opts = { cursor: _cursor, limit: 20, pillar: _pillar || undefined };

      if (API.isLoggedIn() && API.hasOnboarded()) {
        data = await API.feed(opts);
      } else {
        data = await API.articles(opts);
        // Normalise public articles shape to match feed shape
        if (data.items) {
          data = {
            articles: data.items.map(a => ({
              ...a,
              source_name: a.source?.name,
              cached_summary: a.summary_60w,
            })),
            next_cursor: data.next_cursor,
            feed_type: 'fallback',
          };
        }
      }

      if (reset) document.getElementById('feed-list').innerHTML = '';

      const articles = data.articles || data.items || [];
      if (articles.length === 0) {
        _exhausted = true;
        document.getElementById('feed-end').classList.remove('hidden');
      } else {
        _renderBatch(articles);
        _cursor = data.next_cursor || null;
        if (!_cursor) {
          _exhausted = true;
          document.getElementById('feed-end').classList.remove('hidden');
        }
      }
    } catch (err) {
      console.error('Feed load error:', err);
      if (reset) {
        document.getElementById('feed-list').innerHTML = `
          <div class="empty-state">
            <svg width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            <p>Couldn't load feed.<br>Check your connection and try again.</p>
          </div>`;
      }
    } finally {
      _loading = false;
    }
  }

  function setPillar(slug) {
    _pillar = slug;
    load(true);
  }

  function reset() { load(true); }

  return { load, reset, setPillar };
})();
