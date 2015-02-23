
// topic will be woodwind::user:id or woodwind::feed:id
function webSocketSubscribe(topic) {
    if ('WebSocket' in window) {

        var ws = new WebSocket(window.location.origin
                               .replace(/https?:\/\//, 'ws://')
                               .replace(/(:\d+)?$/, ':8077'));

        ws.onopen = function(event) {
            // send the topic
            console.log('subscribing to topic: ' + topic);
            ws.send(topic);
        };

        ws.onmessage = function(event) {
            var data = JSON.parse(event.data);
            data.entries.forEach(function(entryHtml) {
                $('body main').prepend(entryHtml);
            });
        };
    }
}
