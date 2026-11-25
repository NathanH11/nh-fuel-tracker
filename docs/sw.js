const CACHE = "fuel-v5";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icon-v2-192.png", "icon-v2-512.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL))); self.skipWaiting(); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(k => Promise.all(k.filter(x => x !== CACHE).map(x => caches.delete(x))))); self.clients.claim(); });
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || req.url.includes("tile.openstreetmap.org")) return;
  // leave the journey planner's lookups (routing, postcodes, place search) alone: only handle our own files and the map library
  if (new URL(req.url).origin !== location.origin && !req.url.includes("cdnjs.cloudflare.com")) return;
  // Network first (fresh prices), fall back to the last saved copy when offline
  e.respondWith(fetch(req).then(res => {
    const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
    return res;
  }).catch(() => caches.match(req).then(r => r || caches.match("index.html"))));
});
