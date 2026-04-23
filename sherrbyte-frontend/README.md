## SherrByte Frontend — Phase F

### Files
```
index.html          Main HTML shell
css/app.css         All styles — dark editorial aesthetic
js/api.js           API client with JWT auto-refresh
js/events.js        Interaction event tracker (batched)
js/feed.js          Feed renderer (hero cards + trending rows)
js/app.js           App controller (screens, routing, article detail)
manifest.json       PWA manifest
sw.js               Service worker (offline + caching)
firebase.json       Firebase Hosting config
assets/             Put your icons here (icon-192.png, icon-512.png)
```

---

### Quick Deploy to Firebase

```bash
# 1. Install Firebase CLI (once)
npm install -g firebase-tools

# 2. Login
firebase login

# 3. Inside this folder — init (select "Hosting", use existing project)
firebase init hosting
# public directory: .  (dot — current folder)
# single page app: Yes
# overwrite index.html: No

# 4. Deploy
firebase deploy --only hosting
```

Your app will be live at `https://YOUR-PROJECT.web.app`

---

### Change the API URL

In `js/api.js`, line 7:
```js
const BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://sherrbyte-api.fly.dev';   // ← change this if your Fly app name differs
```

---

### Add Icons (for home screen install)

Create two PNG images:
- `assets/icon-192.png` — 192×192px
- `assets/icon-512.png` — 512×512px

Both should be the SherrByte logo on a `#080B14` dark background.
Without icons, the PWA will still install but use a default icon.

---

### What works right now

| Feature | Status |
|---------|--------|
| Auth (login / register) | ✅ |
| Topic onboarding | ✅ |
| Personalised feed (`/v1/feed`) | ✅ |
| Public fallback feed (`/v1/articles`) | ✅ |
| Hero cards + Trending rows | ✅ |
| Article detail with WWWW snapshot | ✅ |
| Infinite scroll + pagination | ✅ |
| Interaction tracking (open/dwell/save/hide) | ✅ |
| PWA install (Android + iOS) | ✅ |
| Offline shell | ✅ |
| Pillar nav filter | ✅ |
| Save / hide / mute-source actions | ✅ |
| JWT auto-refresh | ✅ |
| Skeleton loaders | ✅ |

### Install on Android
1. Open Chrome → visit your Firebase URL
2. Chrome shows "Add to Home Screen" banner automatically
3. Tap Add → icon appears on home screen, opens like a real app

### Install on iOS
1. Open Safari → visit your Firebase URL
2. Tap Share button → "Add to Home Screen"
3. Tap Add → appears on home screen
