from . import tasks
from .extensions import db
from .models import Feed
from flask import Blueprint, request, abort, current_app, make_response
import datetime


push = Blueprint('push', __name__)


@push.route('/_notify/<int:feed_id>', methods=['GET', 'POST'])
def notify(feed_id):
    current_app.logger.debug(
        'received PuSH notification for feed id %d', feed_id)
    feed = Feed.query.get(feed_id)
    if not feed:
        current_app.logger.debug(
            'could not find feed corresponding to %d', feed_id)
        abort(404)

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

        if mode == 'subscribe' and topic == feed.push_topic:
            current_app.logger.debug(
                'PuSH verify subscribe for feed=%r, topic=%s', feed, topic)
            feed.push_verified = True
            if lease_seconds:
                feed.push_expiry = datetime.datetime.utcnow() \
                    + datetime.timedelta(seconds=int(lease_seconds))
            db.session.commit()
            return challenge
        elif mode == 'unsubscribe' and topic != feed.push_topic:
            current_app.logger.debug(
                'PuSH verify unsubscribe for feed=%r, topic=%s', feed, topic)
            return challenge
        current_app.logger.debug('PuSH cannot verify %s for feed=%r, topic=%s',
                                 mode, feed, topic)
        abort(404)

    # could it be? an actual push notification!?
    current_app.logger.debug('received PuSH ping for %r', feed)
    feed.last_pinged = datetime.datetime.utcnow()
    db.session.commit()
    tasks.q.enqueue(tasks.update_feed, feed.id)
    return make_response('', 204)
