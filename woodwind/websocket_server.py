import websockets
import asyncio
import asyncio_redis


@asyncio.coroutine
def handle_subscription(websocket, path):
    topic = yield from websocket.recv()
    redis = yield from asyncio_redis.Connection.create()
    ps = yield from redis.start_subscribe()
    yield from ps.subscribe(['woodwind_notify:' + topic])
    while True:
        message = yield from ps.next_published()
        if not websocket.open:
            break
        yield from websocket.send(message.value)
    redis.close()


asyncio.get_event_loop().run_until_complete(
    websockets.serve(handle_subscription, 'localhost', 8077))
asyncio.get_event_loop().run_forever()
