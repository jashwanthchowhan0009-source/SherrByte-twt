/* ── SherrByte Service Worker ─────────────────────────────────────────────
   Cache-first for static assets, network-first for API calls.
   Enables: home screen install, offline shell, fast repeat loads.
────────────────────────────────────────────────────────────────────────── */

const CACHE    = 'sb-v1';
const STATIC   = ['/', '/index.html', '/css/app.css', '/js/api.js', '/js/events.js', '/js/feed.js', '/js/app.js', '/manifest.json'];
const API_HOST = 'sherrbyte-api.fly.dev';

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // API calls: network-first, no cache
  if (url.hostname === API_HOST || url.pathname.startsWith('/v1/')) {
    e.respondWith(fetch(e.request).catch(() => new Response('{"error":"offline"}', { headers: {'Content-Type':'application/json'} })));
    return;
  }

  // Static assets: cache-first
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      });
    })
  );
});
