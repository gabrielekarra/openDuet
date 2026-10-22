// Installable shell, with deliberately no caching of authenticated content or credentials.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
