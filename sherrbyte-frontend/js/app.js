/* ── SherrByte App Controller ─────────────────────────────────────────────
   Orchestrates all screens: splash → auth → onboarding → main feed.
   Handles: article detail view, pillar nav, bottom nav, scroll events.
────────────────────────────────────────────────────────────────────────── */

const App = (() => {

  // ── SCREEN MANAGEMENT ──
  function show(id) {
    document.querySelectorAll('.screen').forEach(s => s.classList.add('hidden'));
    const el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
  }

  // ── TOAST ──
  let _toastTimer;
  function toast(msg, duration = 2200) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.remove('hidden');
    requestAnimationFrame(() => t.classList.add('show'));
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(() => {
      t.classList.remove('show');
      setTimeout(() => t.classList.add('hidden'), 300);
    }, duration);
  }

  // ── AUTH SCREEN ──
  function initAuth() {
    // Tab switching
    document.querySelectorAll('.auth-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const target = tab.dataset.tab;
        document.getElementById('login-form').classList.toggle('hidden',    target !== 'login');
        document.getElementById('register-form').classList.toggle('hidden', target !== 'register');
      });
    });

    // Login
    document.getElementById('btn-login').addEventListener('click', async () => {
      const email = document.getElementById('login-email').value.trim();
      const pass  = document.getElementById('login-password').value;
      const errEl = document.getElementById('login-error');
      const btn   = document.getElementById('btn-login');
      errEl.classList.add('hidden');
      btn.textContent = 'Signing in…'; btn.disabled = true;
      try {
        const user = await API.login(email, pass);
        await _postLogin(user);
      } catch (e) {
        errEl.textContent = e.message || 'Sign in failed. Check your credentials.';
        errEl.classList.remove('hidden');
      } finally {
        btn.textContent = 'Sign In'; btn.disabled = false;
      }
    });

    // Register
    document.getElementById('btn-register').addEventListener('click', async () => {
      const name  = document.getElementById('reg-name').value.trim();
      const email = document.getElementById('reg-email').value.trim();
      const pass  = document.getElementById('reg-password').value;
      const errEl = document.getElementById('reg-error');
      const btn   = document.getElementById('btn-register');
      errEl.classList.add('hidden');
      btn.textContent = 'Creating…'; btn.disabled = true;
      try {
        const user = await API.register(email, pass, name);
        await _postLogin(user);
      } catch (e) {
        errEl.textContent = e.message || 'Registration failed.';
        errEl.classList.remove('hidden');
      } finally {
        btn.textContent = 'Create Account'; btn.disabled = false;
      }
    });

    // Enter key support
    ['login-password', 'reg-password'].forEach(id => {
      document.getElementById(id).addEventListener('keydown', e => {
        if (e.key === 'Enter') {
          const btn = id.startsWith('login') ? 'btn-login' : 'btn-register';
          document.getElementById(btn).click();
        }
      });
    });
  }

  async function _postLogin(user) {
    if (!user.onboarding_completed) {
      await _loadTaxonomy();
      show('onboarding-screen');
    } else {
      await _initMainApp(user);
    }
  }

  // ── ONBOARDING ──
  let _selectedTopics = new Set();

  async function _loadTaxonomy() {
    try {
      const { microtopics } = await API.taxonomy();
      const grid = document.getElementById('topic-grid');
      grid.innerHTML = '';
      microtopics.forEach(mt => {
        const chip = document.createElement('button');
        chip.className = 'topic-chip';
        chip.dataset.slug = mt.slug;
        chip.textContent = mt.name_en;
        chip.addEventListener('click', () => _toggleTopic(chip, mt.slug));
        grid.appendChild(chip);
      });
    } catch (e) {
      console.error('Taxonomy load failed:', e);
    }
  }

  function _toggleTopic(chip, slug) {
    if (_selectedTopics.has(slug)) {
      _selectedTopics.delete(slug);
      chip.classList.remove('selected');
    } else {
      _selectedTopics.add(slug);
      chip.classList.add('selected');
    }
    const n = _selectedTopics.size;
    document.getElementById('ob-count').textContent = `${n} selected`;
    document.getElementById('btn-ob-continue').disabled = n < 5;
  }

  function initOnboarding() {
    document.getElementById('btn-ob-continue').addEventListener('click', async () => {
      const btn = document.getElementById('btn-ob-continue');
      btn.textContent = 'Setting up…'; btn.disabled = true;
      try {
        await API.selectTopics([..._selectedTopics]);
        const user = API.getUser();
        await _initMainApp(user);
      } catch (e) {
        toast('Something went wrong. Try again.'); btn.disabled = false; btn.textContent = 'Continue →';
      }
    });
  }

  // ── MAIN APP ──
  async function _initMainApp(user) {
    // Set avatar
    const initials = (user?.display_name || user?.email || 'U').charAt(0).toUpperCase();
    document.getElementById('user-avatar').textContent = initials;

    show('app');
    await _loadPillarNav();
    Feed.load(true);
    _initInfiniteScroll();
    _initScrollBehaviour();
  }

  // ── PILLAR NAV ──
  async function _loadPillarNav() {
    try {
      const { pillars } = await API.taxonomy();
      const track = document.getElementById('pillar-track');
      pillars.forEach(p => {
        const btn = document.createElement('button');
        btn.className = 'pillar-btn';
        btn.dataset.pillar = p.slug;
        btn.textContent = `${p.icon || ''} ${p.name_en}`.trim();
        btn.addEventListener('click', () => _selectPillar(btn, p.slug));
        track.appendChild(btn);
      });
    } catch {}
  }

  function _selectPillar(btn, slug) {
    document.querySelectorAll('.pillar-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    btn.scrollIntoView({ inline: 'center', behavior: 'smooth' });
    Feed.setPillar(slug);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ── BOTTOM NAV ──
  function initBottomNav() {
    document.querySelectorAll('.nav-item').forEach(item => {
      item.addEventListener('click', () => {
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        const view = item.dataset.view;
        if (view === 'feed') { window.scrollTo({ top: 0, behavior: 'smooth' }); }
        // saved / profile / trending: extend in Phase G
      });
    });
  }

  // ── INFINITE SCROLL ──
  function _initInfiniteScroll() {
    const trigger = document.getElementById('load-more-trigger');
    const obs = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) Feed.load();
    }, { rootMargin: '400px' });
    obs.observe(trigger);
  }

  // ── SCROLL BEHAVIOUR ──
  function _initScrollBehaviour() {
    let lastY = 0;
    window.addEventListener('scroll', () => {
      const y = window.scrollY;
      const topbar = document.getElementById('topbar');
      topbar.classList.toggle('scrolled', y > 40);
      lastY = y;
    }, { passive: true });
  }

  // ── ARTICLE DETAIL ──
  let _dwellArticleId = null;

  function openArticle(art) {
    const id      = art.id;
    const title   = art.headline_rewrite || art.title || 'Untitled';
    const summary = art.cached_summary   || art.summary_60w || '';
    const img     = art.image_url || '';
    const source  = art.source?.name || art.source_name || '';
    const time    = _ago(art.published_at);
    const url     = art.url || '#';
    const wwww    = art.wwww || null;
    const tags    = art.tags || [];

    const detail = document.getElementById('detail-content');
    detail.innerHTML = `
      ${img ? `<img class="detail-hero-img" src="${img}" alt="" loading="lazy">` : ''}
      <div class="detail-source-bar">
        <span class="detail-source">${source}</span>
        ${time ? `<span class="card-dot" style="background:var(--text-muted);margin:0 4px;width:3px;height:3px;border-radius:50%;display:inline-block;"></span><span class="detail-time">${time}</span>` : ''}
      </div>
      <h1 class="detail-title">${title}</h1>
      ${wwww ? _buildWWWW(wwww) : ''}
      ${summary ? `<p class="detail-summary">${summary}</p>` : ''}
      ${tags.length ? `<div class="detail-tags">${tags.map(t=>`<span class="detail-tag">${t.microtopic_name||t}</span>`).join('')}</div>` : ''}
      <a class="detail-read-more" href="${url}" target="_blank" rel="noopener">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
        Read full article on ${source}
      </a>
    `;

    // Save button state
    const saved = JSON.parse(localStorage.getItem('sb_saved') || '[]');
    document.getElementById('btn-save-article').classList.toggle('active', saved.includes(id));

    const screen = document.getElementById('article-detail');
    screen.classList.remove('hidden');
    requestAnimationFrame(() => screen.classList.add('open'));

    // Dwell tracking
    _dwellArticleId = id;
    Tracker.open(id, art.source?.id || null);
    Tracker.startDwell(id);

    // Scroll tracking
    const scrollHandler = () => {
      const pct = Math.round((window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100);
      Tracker.updateScroll(id, pct);
    };
    window.addEventListener('scroll', scrollHandler, { passive: true });
    screen._scrollHandler = scrollHandler;
  }

  function _buildWWWW(wwww) {
    const rows = [
      ['WHAT', wwww.what], ['WHO', wwww.who], ['WHERE', wwww.where],
      ['WHEN', wwww.when], ['WHY', wwww.why],
    ].filter(([, v]) => v);
    if (!rows.length) return '';
    return `<div class="detail-wwww">
      <div class="detail-wwww-title">Story Snapshot</div>
      ${rows.map(([k,v])=>`<div class="wwww-row"><span class="wwww-key">${k}</span><span class="wwww-val">${v}</span></div>`).join('')}
    </div>`;
  }

  function _closeDetail() {
    const screen = document.getElementById('article-detail');
    screen.classList.remove('open');
    if (_dwellArticleId) {
      Tracker.endDwell(_dwellArticleId);
      _dwellArticleId = null;
    }
    if (screen._scrollHandler) {
      window.removeEventListener('scroll', screen._scrollHandler);
    }
    setTimeout(() => screen.classList.add('hidden'), 320);
  }

  function _ago(dateStr) {
    if (!dateStr) return '';
    const diff = (Date.now() - new Date(dateStr)) / 1000;
    if (diff < 60)    return 'Just now';
    if (diff < 3600)  return `${Math.floor(diff/60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
    return `${Math.floor(diff/86400)}d ago`;
  }

  // ── SHARE ──
  async function shareArticle(art) {
    const title = art.headline_rewrite || art.title || 'SherrByte Article';
    const url   = art.url || window.location.href;
    try {
      if (navigator.share) {
        await navigator.share({ title, url });
        Tracker.share(art.id);
      } else {
        await navigator.clipboard.writeText(url);
        toast('Link copied!');
        Tracker.share(art.id);
      }
    } catch {}
  }

  // ── INIT ──
  async function init() {
    // Wait for splash animation
    setTimeout(async () => {
      initAuth();
      initOnboarding();
      initBottomNav();

      // Detail back button
      document.getElementById('btn-back').addEventListener('click', _closeDetail);
      document.getElementById('btn-share-article').addEventListener('click', () => {
        const id = document.querySelector('#article-detail [data-current-id]');
        // minimal share — extend as needed
        shareArticle({ url: document.querySelector('.detail-read-more')?.href });
      });

      // Handle logout event
      window.addEventListener('sb:logout', () => show('auth-screen'));

      if (API.isLoggedIn()) {
        try {
          const user = await API.me();
          await _postLogin(user);
        } catch {
          show('auth-screen');
        }
      } else {
        show('auth-screen');
      }
    }, 2000);   // match splash animation duration
  }

  return { init, toast, openArticle };
})();

// ── BOOT ──
document.addEventListener('DOMContentLoaded', () => App.init());
