// Nexa CRM Pro Service Worker (PWA)
const CACHE_NAME = 'nexa-crm-pro-v1';

const STATIC_ASSETS = [
  '/crm',
  '/crm-manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/icon-maskable-512.png',
  '/static/yigit_narin_portrait.png',
  'https://cdn.tailwindcss.com',
  'https://unpkg.com/vue@3/dist/vue.global.js',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn('[Nexa CRM SW] Bazı statik varlıklar önbelleğe alınırken atlandı:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((k) => {
          if (k !== CACHE_NAME) {
            console.log('[Nexa CRM SW] Eski önbellek temizleniyor:', k);
            return caches.delete(k);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Ignore non-GET and chrome-extension
  if (req.method !== 'GET' || url.protocol.startsWith('chrome-extension')) {
    return;
  }

  // API endpoints: Network-first with cache fallback
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/download/')) {
    event.respondWith(
      fetch(req).catch(() => {
        return caches.match(req).then((cached) => {
          return cached || new Response(JSON.stringify({ error: 'Çevrimdışı mod: İnternet bağlantınızı kontrol edin' }), {
            headers: { 'Content-Type': 'application/json' }
          });
        });
      })
    );
    return;
  }

  // HTML Pages: Stale-while-revalidate or Network-first
  if (req.mode === 'navigate' || req.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(req).then((res) => {
        if (res && res.status === 200) {
          const resClone = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(req, resClone));
        }
        return res;
      }).catch(() => {
        return caches.match(req).then((cached) => cached || caches.match('/crm'));
      })
    );
    return;
  }

  // Static Assets: Cache-first with network fallback
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req).then((res) => {
        if (res && res.status === 200 && (url.origin === location.origin || url.hostname.includes('cdn') || url.hostname.includes('fonts'))) {
          const resClone = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(req, resClone));
        }
        return res;
      });
    })
  );
});
