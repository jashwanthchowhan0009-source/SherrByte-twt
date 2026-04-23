/* ── SherrByte API Client ──────────────────────────────────────────────────
   Single source of truth for all backend calls.
   Handles: JWT storage, auto-refresh, retry on 401, event batching.
────────────────────────────────────────────────────────────────────────── */

const API = (() => {
  // ── CONFIG ── change this to your Fly.io URL in production
 const API_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'https://sherrbyte-twt.onrender.com';

  // ── TOKEN STORAGE ──
  let _access  = localStorage.getItem('sb_access')  || '';
  let _refresh = localStorage.getItem('sb_refresh') || '';
  let _user    = JSON.parse(localStorage.getItem('sb_user') || 'null');

  function saveTokens({ access_token, refresh_token }) {
    _access  = access_token;
    _refresh = refresh_token;
    localStorage.setItem('sb_access',  access_token);
    localStorage.setItem('sb_refresh', refresh_token);
  }

  function saveUser(user) {
    _user = user;
    localStorage.setItem('sb_user', JSON.stringify(user));
  }

  function clearAuth() {
    _access = _refresh = '';
    _user   = null;
    localStorage.removeItem('sb_access');
    localStorage.removeItem('sb_refresh');
    localStorage.removeItem('sb_user');
  }

  function getUser()        { return _user; }
  function isLoggedIn()     { return !!_access; }
  function hasOnboarded()   { return _user?.onboarding_completed || false; }

  // ── CORE FETCH ──
  let _refreshing = null;   // deduplicate concurrent refresh attempts

  async function _fetch(path, opts = {}, retry = true) {
    const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
    if (_access) headers['Authorization'] = `Bearer ${_access}`;

    const res = await fetch(`${BASE}${path}`, { ...opts, headers });

    if (res.status === 401 && retry && _refresh) {
      // Try to refresh once
      if (!_refreshing) {
        _refreshing = _doRefresh().finally(() => { _refreshing = null; });
      }
      const ok = await _refreshing;
      if (ok) return _fetch(path, opts, false);
      clearAuth();
      window.dispatchEvent(new Event('sb:logout'));
      return res;
    }

    return res;
  }

  async function _doRefresh() {
    try {
      const res = await fetch(`${BASE}/v1/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: _refresh }),
      });
      if (!res.ok) return false;
      const { access_token, refresh_token } = await res.json();
      saveTokens({ access_token, refresh_token });
      return true;
    } catch { return false; }
  }

  async function json(path, opts = {}) {
    const res = await _fetch(path, opts);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw Object.assign(new Error(err?.error?.message || `HTTP ${res.status}`), { status: res.status });
    }
    if (res.status === 204) return null;
    return res.json();
  }

  // ── AUTH ──
  async function login(email, password) {
    const data = await json('/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    saveTokens(data.tokens);
    saveUser(data.user);
    return data.user;
  }

  async function register(email, password, display_name) {
    const data = await json('/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name }),
    });
    saveTokens(data.tokens);
    saveUser(data.user);
    return data.user;
  }

  async function logout() {
    try {
      await json('/v1/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: _refresh }),
      });
    } catch {}
    clearAuth();
  }

  async function me() {
    const user = await json('/v1/auth/me');
    saveUser(user);
    return user;
  }

  // ── TAXONOMY ──
  async function taxonomy() {
    return json('/v1/taxonomy');
  }

  // ── FEED ──
  async function feed({ cursor, limit = 20, pillar } = {}) {
    const params = new URLSearchParams({ limit });
    if (cursor) params.set('cursor', cursor);
    if (pillar)  params.set('pillar', pillar);
    return json(`/v1/feed?${params}`);
  }

  async function articles({ cursor, limit = 20, pillar } = {}) {
    // Fallback: public articles endpoint (no auth needed)
    const params = new URLSearchParams({ limit });
    if (cursor) params.set('cursor', cursor);
    if (pillar)  params.set('pillar', pillar);
    return json(`/v1/articles?${params}`);
  }

  // ── ONBOARDING ──
  async function onboardingStatus() {
    return json('/v1/onboarding/status');
  }

  async function selectTopics(topic_slugs) {
    await json('/v1/onboarding/topics', {
      method: 'POST',
      body: JSON.stringify({ topic_slugs }),
    });
    // Mark user as onboarded locally
    if (_user) { _user.onboarding_completed = true; saveUser(_user); }
  }

  return {
    getUser, isLoggedIn, hasOnboarded, clearAuth,
    login, register, logout, me,
    taxonomy, feed, articles,
    onboardingStatus, selectTopics,
  };
})();
