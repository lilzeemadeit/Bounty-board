// Bounty Board service worker: the app opens offline, and card images you've seen are kept for offline use.
const APP = "bb-app-v1", IMG = "bb-img-v1";
self.addEventListener("install", e => { self.skipWaiting(); e.waitUntil(caches.open(APP).then(c => c.addAll(["./", "./manifest.webmanifest", "./icon-192.png"]))); });
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  const req = e.request; if (req.method !== "GET") return;
  const u = new URL(req.url);
  if (u.origin === location.origin){        // the app itself: newest when online, saved copy when offline
    e.respondWith(fetch(req).then(r => { const cp = r.clone(); caches.open(APP).then(c => c.put(req, cp)); return r; })
      .catch(() => caches.match(req).then(r => r || caches.match("./"))));
    return;
  }
  if (/onepiece-cardgame\.com$/.test(u.hostname)){   // card art: keep what you've looked at
    e.respondWith(caches.open(IMG).then(async c => { const hit = await c.match(req); if (hit) return hit;
      const r = await fetch(req); if (r.ok || r.type === "opaque") c.put(req, r.clone()); return r; }));
  }
});
