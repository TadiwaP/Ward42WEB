/*
  sw.js - the service worker.

  A service worker is a script the browser runs in the background, between
  our pages and the network. Ours does two jobs:
    1. It keeps a copy of the "app shell" (CSS, JavaScript, icons and a
       friendly offline page) so the app still opens with no signal.
    2. When a page cannot be loaded because the phone is offline, it shows
       the offline page instead of the browser's dinosaur error page.
       (Study Guide, Section 8.3)

  It deliberately does NOT keep copies of reports, photos, the coordinator
  pages or any API answers. Those hold personal information (POPIA), and we
  do not want them stored in a cache on a phone that may be shared.

  When you change any file in SHELL_FILES, change the number in CACHE_NAME
  (v1 -> v2) so phones throw away the old copies.
*/

var CACHE_NAME = "ward42-shell-v1";

var SHELL_FILES = [
  "/offline",
  "/static/css/styles.css",
  "/static/js/app.js",
  "/static/vendor/bootstrap/bootstrap.min.css",
  "/static/vendor/bootstrap/bootstrap.bundle.min.js",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png"
];

// 1. Install: save the app shell the first time the worker starts.
self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function (cache) { return cache.addAll(SHELL_FILES); })
      .then(function () { return self.skipWaiting(); })
  );
});

// 2. Activate: delete copies left over from older versions.
self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys()
      .then(function (names) {
        return Promise.all(
          names
            .filter(function (name) { return name !== CACHE_NAME; })
            .map(function (name) { return caches.delete(name); })
        );
      })
      .then(function () { return self.clients.claim(); })
  );
});

// 3. Fetch: runs every time the page asks for something.
self.addEventListener("fetch", function (event) {
  var request = event.request;
  var url = new URL(request.url);

  // Only deal with requests to our own site.
  if (url.origin !== self.location.origin) {
    return;
  }

  // A page is being opened (or a form is being sent). Try the network. If
  // that fails, we are offline, so show the offline page.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(function () {
        return caches.match("/offline");
      })
    );
    return;
  }

  // CSS, JavaScript and icons: network first, so changes show straight away.
  // The browser only re-downloads a file if it changed. If the network
  // fails, use the saved copy. Video files are left to the browser, because
  // they are big and are played in pieces.
  var isShellFile =
    request.method === "GET" &&
    url.pathname.indexOf("/static/") === 0 &&
    url.pathname.indexOf("/static/media/") !== 0;

  if (isShellFile) {
    event.respondWith(
      fetch(request)
        .then(function (response) {
          if (response.status === 200) {
            var copy = response.clone();
            caches.open(CACHE_NAME).then(function (cache) { cache.put(request, copy); });
          }
          return response;
        })
        .catch(function () {
          return caches.match(request);
        })
    );
  }
});
