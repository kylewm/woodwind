from aiohttp import web
import asyncio
import asyncio_redis


@asyncio.coroutine
def handle_subscription(request):
    topic = request.GET['topic']
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/event-stream'
    response.start(request)
    redis = yield from asyncio_redis.Connection.create()
    try:
        ps = yield from redis.start_subscribe()
        yield from ps.subscribe(['woodwind_notify:' + topic])
        while True:
            message = yield from ps.next_published()
            response.write(
                'data: {}\n\n'.format(message.value).encode('utf-8'))
    finally:
        redis.close()


app = web.Application()
app.router.add_route('GET', '/', handle_subscription)

loop = asyncio.get_event_loop()
srv = loop.run_until_complete(
    loop.create_server(app.make_handler(), '0.0.0.0', 8077))
loop.run_forever()
