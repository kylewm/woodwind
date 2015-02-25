import itertools
import json
import redis
import threading
import tornado.ioloop
import tornado.websocket


SUBSCRIBERS = {}


def redis_loop():
    r = redis.StrictRedis()
    ps = r.pubsub()
    ps.subscribe('woodwind_notify')
    for message in ps.listen():
        if message['type'] == 'message':
            msg_data = str(message.get('data'), 'utf-8')
            msg_blob = json.loads(msg_data)
            user_topic = 'user:{}'.format(msg_blob.get('user'))
            feed_topic = 'feed:{}'.format(msg_blob.get('feed'))
            for subscriber in itertools.chain(
                    SUBSCRIBERS.get(user_topic, []),
                    SUBSCRIBERS.get(feed_topic, [])):
                tornado.ioloop.IOLoop.instance().add_callback(
                    lambda: subscriber.forward_message(msg_data))


class WSHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def forward_message(self, message):
        self.write_message(message)

    def on_message(self, topic):
        self.topic = topic
        SUBSCRIBERS.setdefault(topic, []).append(self)

    def on_close(self):
        if hasattr(self, 'topic'):
            SUBSCRIBERS.setdefault(self.topic, []).append(self)


application = tornado.web.Application([
    (r'/', WSHandler),
])


if __name__ == '__main__':
    threading.Thread(target=redis_loop).start()
    application.listen(8077)
    tornado.ioloop.IOLoop.instance().start()
