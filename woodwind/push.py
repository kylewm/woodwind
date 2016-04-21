from . import tasks
from .extensions import db
from .models import Feed
from flask import Blueprint, request, abort, current_app, make_response
import datetime
import hmac


push = Blueprint('push', __name__)


@push.route('/_notify/<int:feed_id>', methods=['GET', 'POST'])
def notify(feed_id):
    current_app.logger.debug(
        'received PuSH notification for feed id %d', feed_id)
    feed = Feed.query.get(feed_id)

    current_app.logger.debug('processing PuSH notification for feed %r', feed)
    if request.method == 'GET':
        # verify subscribe or unsusbscribe
        mode = request.args.get('hub.mode')
        topic = request.args.get('hub.topic')
        challenge = request.args.get('hub.challenge')
        lease_seconds = request.args.get('hub.lease_seconds')
        current_app.logger.debug(
            'PuSH verification. feed=%r, mode=%s, topic=%s, '
            'challenge=%s, lease_seconds=%s',
            feed, mode, topic, challenge, lease_seconds)

        if mode == 'subscribe':
            if not feed:
                current_app.logger.warn(
                    'could not find feed corresponding to %d', feed_id)
                return make_response('no feed with id %d' % feed_id, 400)

            if topic != feed.push_topic:
                current_app.logger.warn(
                    'feed topic (%s) does not match subscription request (%s)',
                    feed.push_topic, topic)
                return make_response(
                    'topic %s does not match subscription request %s' % (feed.push_topic, topic), 400)

            current_app.logger.debug(
                'PuSH verify subscribe for feed=%r, topic=%s', feed, topic)
            feed.push_verified = True
            if lease_seconds:
                feed.push_expiry = datetime.datetime.utcnow() \
                    + datetime.timedelta(seconds=int(lease_seconds))
            db.session.commit()
            return challenge

        elif mode == 'unsubscribe':
            if not feed or topic != feed.push_topic:
                current_app.logger.debug(
                    'PuSH verify unsubscribe for feed=%r, topic=%s', feed, topic)
                return challenge
            else:
                current_app.logger.debug(
                    'PuSH denying unsubscribe for feed=%r, topic=%s', feed, topic)
                return make_response('unsubscribe denied', 400)

        elif mode:
            current_app.logger.debug('PuSH request with unknown mode %s', mode)
            return make_response('unrecognized hub.mode=%s' % mode, 400)

        else:
            current_app.logger.debug('PuSH request with no mode')
            return make_response('missing requred parameter hub.mode', 400)

    if not feed:
        current_app.logger.warn(
            'could not find feed corresponding to %d', feed_id)
        return make_response('no feed with id %d' % feed_id, 400)

    # could it be? an actual push notification!?
    current_app.logger.debug(
        'received PuSH ping for %r; content size: %d', feed, len(request.data))

    # try to process fat pings
    content = None
    content_type = None
    signature = request.headers.get('X-Hub-Signature')
    if signature and feed.push_secret and request.data:
        expected = 'sha1=' + hmac.new(feed.push_secret.encode('utf-8'),
                     msg=request.data, digestmod='sha1').hexdigest()
        if expected != signature:
            current_app.logger.warn(
                'X-Hub-Signature (%s) did not match expected (%s)',
                signature, expected)
            return make_response('', 204)
        current_app.logger.info('Good X-Hub-Signature!')
        content_type = request.headers.get('Content-Type')
        current_app.logger.info('PuSH content type: %s', content_type)
        content = request.data.decode('utf-8')

    tasks.q_high.enqueue(tasks.update_feed, feed.id,
                         content=content, content_type=content_type,
                         is_polling=False)
    feed.last_pinged = datetime.datetime.utcnow()
    db.session.commit()
    return make_response('', 204)
