// © 2026 Torsten Michaely - KFZ Kontakt Service Worker
// Mit WhatsApp-Integration für flexible Kontaktmöglichkeiten
// All rights reserved

const CACHE_VERSION = 'kfz-kontakt-1.0.124';
const CACHE_NAME = `${CACHE_VERSION}-v1`;
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const DYNAMIC_CACHE = `${CACHE_VERSION}-dynamic`;

// Dateien zum Caching beim Installation
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/offline.html',
  '/manifest.json',
  '/dashboard/index.html',
  '/dashboard/css/style.css',
  '/dashboard/js/app.js',
  '/qr/contact-form.html',
  '/qr/select-category.html',
  '/qr/vehicle-landing.html',
  '/datenschutz.html',
  '/impressum.html',
  '/assets/favicon.svg'
];

// Installation: Cache statische Dateien
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installiere:', CACHE_NAME);
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[Service Worker] Cache statische Dateien');
        return cache.addAll(STATIC_ASSETS).catch((err) => {
          console.warn('[Service Worker] Fehler beim Caching einiger Dateien:', err);
        });
      })
      .then(() => self.skipWaiting())
  );
});

// Aktivierung: Alte Caches löschen
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Aktiviere:', CACHE_NAME);
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE && cacheName.startsWith('kfz-kontakt')) {
              console.log('[Service Worker] Lösche alten Cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch: Cache-First für Seiten, Network-First für API
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API-Anfragen: Network-First mit Fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const cache = caches.open(DYNAMIC_CACHE);
            cache.then((c) => c.put(request, response.clone()));
          }
          return response;
        })
        .catch(() => {
          return caches.match(request)
            .then((cached) => cached || createOfflineResponse());
        })
    );
    return;
  }

  // Statische Assets: Cache-First
  if (request.method === 'GET' &&
      (url.pathname.endsWith('.css') ||
       url.pathname.endsWith('.js') ||
       url.pathname.endsWith('.png') ||
       url.pathname.endsWith('.jpg') ||
       url.pathname.endsWith('.ico'))) {
    event.respondWith(
      caches.match(request)
        .then((cached) => cached || fetch(request)
          .then((response) => {
            if (response.ok) {
              const cache = caches.open(STATIC_CACHE);
              cache.then((c) => c.put(request, response.clone()));
            }
            return response;
          })
        )
    );
    return;
  }

  // HTML-Seiten: Cache mit Network-Fallback
  if (request.mode === 'navigate' || request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const cache = caches.open(DYNAMIC_CACHE);
            cache.then((c) => c.put(request, response.clone()));
          }
          return response;
        })
        .catch(() => {
          return caches.match(request)
            .then((cached) => cached || caches.match('/offline.html'));
        })
    );
    return;
  }

  // Sonstige: Standard Fetch
  event.respondWith(fetch(request));
});

// Hilfsfunktion für Offline-Response
function createOfflineResponse() {
  return new Response(
    '<html><body><h1>Offline</h1><p>Du bist offline. Versuche es später erneut.</p></body></html>',
    { headers: { 'Content-Type': 'text/html' } }
  );
}

// Nachrichten vom Client
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
