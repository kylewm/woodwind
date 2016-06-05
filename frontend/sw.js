var version = 'v2';

this.addEventListener('install', function (event) {
    event.waitUntil(
        caches.open(version).then(function (cache) {
            return cache.addAll([
                '/static/logo.png',
                '/static/style.css',
                '/offline',
            ])
        })
    );
})

this.addEventListener('fetch', function (event) {
    console.log('caught fetch: ' + event)
    event.respondWith(
        caches.match(event.request)
        .then(function (response) {
            console.log('cache got response: ' + response)
            return response || fetch(event.request);
        })
        .then(function (response) {
            console.log('fetch got response: ' + response)
            return response
        })
        .catch(function (err) {
            return caches.match('/offline')
        })
    )
})