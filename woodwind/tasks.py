from config import Config
from contextlib import contextmanager
from woodwind.models import Feed, Entry
from redis import StrictRedis
import bs4
import celery
import celery.utils.log
import datetime
import feedparser
import json
import mf2py
import mf2util
import re
import sqlalchemy
import sqlalchemy.orm
import time
import urllib.parse
import requests


UPDATE_INTERVAL = datetime.timedelta(hours=1)
TWITTER_RE = re.compile(
    r'https?://(?:www\.|mobile\.)?twitter\.com/(\w+)/status(?:es)?/(\w+)')

app = celery.Celery('woodwind')
app.config_from_object('celeryconfig')

logger = celery.utils.log.get_task_logger(__name__)
engine = sqlalchemy.create_engine(Config.SQLALCHEMY_DATABASE_URI)
Session = sqlalchemy.orm.sessionmaker(bind=engine)

redis = StrictRedis()


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


@app.task
def tick():
    with session_scope() as session:
        now = datetime.datetime.utcnow()
        logger.debug('Tick {}'.format(now))
        for feed in session.query(Feed).all():
            logger.debug('Feed {} last checked {}'.format(
                feed, feed.last_checked))
            if (not feed.last_checked
                    or now - feed.last_checked > UPDATE_INTERVAL):
                update_feed.delay(feed.id)


@app.task
def update_feed(feed_id):
    with session_scope() as session:
        feed = session.query(Feed).get(feed_id)
        logger.info('Updating {}'.format(feed))
        process_feed(session, feed)


def process_feed(session, feed):
    now = datetime.datetime.utcnow()
    new_entries = []
    try:
        logger.info('fetching feed: %s', feed)
        response = requests.get(feed.feed)
        if response.status_code // 100 != 2:
            logger.warn('bad response from %s. %r: %r', feed.feed,
                        response, response.text)
            return

        check_push_subscription(session, feed, response)
        backfill = len(feed.entries) == 0  # backfill if this is the first pull
        if feed.type == 'xml':
            result = process_xml_feed_for_new_entries(session, feed,
                                                      response, backfill)
        elif feed.type == 'html':
            result = process_html_feed_for_new_entries(session, feed,
                                                       response, backfill)
        else:
            result = []

        for entry in result:
            old = session.query(Entry)\
                .filter(Entry.feed == feed)\
                .filter(Entry.uid == entry.uid).first()
            # have we seen this post before
            if not old or not is_content_equal(old, entry):
                # set a default value for published if none is provided
                if not entry.published:
                    entry.published = (old and old.published) or now
                if old:
                    # if we're updating an old entriy, use the original
                    # retrieved time
                    entry.retrieved = old.retrieved
                    feed.entries.remove(old)
                    # punt on deleting for now, learn about cascade
                    # and stuff later
                    # session.delete(old)

                feed.entries.append(entry)
                session.commit()

                for in_reply_to in entry.get_property('in-reply-to', []):
                    fetch_reply_context(entry.id, in_reply_to)

                new_entries.append(entry)
            else:
                logger.info('skipping previously seen post %s', old.permalink)

    finally:
        feed.last_checked = now
        if new_entries:
            feed.last_updated = now
        session.commit()
        if new_entries:
            notify_feed_updated(session, feed, new_entries)


def check_push_subscription(session, feed, response):
    def build_callback_url():
        return '{}://{}/_notify/{}'.format(
            getattr(Config, 'PREFERRED_URL_SCHEME', 'http'),
            Config.SERVER_NAME,
            feed.id)

    def send_request(mode, hub, topic):
        logger.debug(
            'sending %s request for hub=%r, topic=%r', mode, hub, topic)
        r = requests.post(hub, data={
            'hub.mode': mode,
            'hub.topic': topic,
            'hub.callback': build_callback_url(),
            'hub.verify': 'sync',  # backcompat with 0.3
            # TODO secret should only be used over HTTPS
            # 'hub.secret': secret,
        })
        logger.debug('%s response %r', mode, r)

    expiry = feed.push_expiry
    old_hub = feed.push_hub
    old_topic = feed.push_topic
    hub = response.links.get('hub', {}).get('url')
    topic = response.links.get('self', {}).get('url')

    logger.debug('link headers. links=%s, hub=%s, topic=%s', response.links, hub, topic)
    if not hub or not topic:
        # try to find link rel elements
        if feed.type == 'html':
            soup = bs4.BeautifulSoup(get_response_content(response))
            if not hub:
                hub_link = soup.find('link', rel='hub')
                hub = hub_link and hub_link.get('href')
            if not topic:
                self_link = soup.find('link', rel='self')
                topic = self_link and self_link.get('href')
        elif feed.type == 'xml':
            parsed = feedparser.parse(get_response_content(response))
            links = parsed.feed.get('links')
            if links:
                if not hub:
                    hub = next((link['href'] for link in links
                                if 'hub' in link['rel']), None)
                if not topic:
                    topic = next((link['href'] for link in links
                                  if 'self' in link['rel']), None)

    if ((expiry and expiry - datetime.datetime.utcnow() <= UPDATE_INTERVAL)
            or hub != old_hub or topic != old_topic or not feed.push_verified):
        feed.push_hub = hub
        feed.push_topic = topic
        feed.push_verified = False
        feed.push_expiry = None
        session.commit()

        if old_hub and old_topic and hub != old_hub and topic != old_topic:
            send_request('unsubscribe', old_hub, old_topic)

        if hub and topic:
            send_request('subscribe', hub, topic)


def notify_feed_updated(session, feed, entries):
    """Render the new entries and publish them to redis
    """
    from . import create_app
    from flask import render_template
    import flask.ext.login as flask_login
    flask_app = create_app()

    for user in feed.users:
        with flask_app.test_request_context():
            flask_login.login_user(user, remember=True)
            message = json.dumps({
                'user': user.id,
                'feed': feed.id,
                'entries': [
                    render_template('_entry.jinja2', feed=feed, entry=e)
                    for e in entries
                ],
            })
            redis.publish('woodwind_notify', message)


def is_content_equal(e1, e2):
    """The criteria for determining if an entry that we've seen before
    has been updated. If any of these fields have changed, we'll scrub the
    old entry and replace it with the updated one.
    """
    return (e1.title == e2.title
            and e1.content == e2.content
            and e1.author_name == e2.author_name
            and e1.author_url == e2.author_url
            and e1.author_photo == e2.author_photo
            and e1.properties == e2.properties)


def process_xml_feed_for_new_entries(session, feed, response, backfill):
    logger.debug('fetching xml feed: %s', feed)

    now = datetime.datetime.utcnow()
    parsed = feedparser.parse(get_response_content(response))
    feed_props = parsed.get('feed', {})
    default_author_url = feed_props.get('author_detail', {}).get('href')
    default_author_name = feed_props.get('author_detail', {}).get('name')
    default_author_photo = feed_props.get('logo')

    logger.debug('found {} entries'.format(len(parsed.entries)))
    for p_entry in parsed.entries:
        logger.debug('processing entry {}'.format(str(p_entry)[:256]))
        permalink = p_entry.get('link')
        uid = p_entry.get('id') or permalink

        if not uid:
            continue

        if 'updated_parsed' in p_entry:
            updated = datetime.datetime.fromtimestamp(
                time.mktime(p_entry.updated_parsed))
        else:
            updated = None

        if 'published_parsed' in p_entry:
            published = datetime.datetime.fromtimestamp(
                time.mktime(p_entry.published_parsed))
        else:
            published = updated

        retrieved = now
        if backfill and published:
            retrieved = published

        title = p_entry.get('title')

        content = None
        content_list = p_entry.get('content')
        if content_list:
            content = content_list[0].value
        else:
            content = p_entry.get('summary')

        if title and content:
            title_trimmed = title.rstrip('...').rstrip('…')
            if content.startswith(title_trimmed):
                title = None

        entry = Entry(
            published=published,
            updated=updated,
            uid=uid,
            permalink=permalink,
            retrieved=retrieved,
            title=p_entry.get('title'),
            content=content,
            author_name=p_entry.get('author_detail', {}).get('name')
            or default_author_name,
            author_url=p_entry.get('author_detail', {}).get('href')
            or default_author_url,
            author_photo=default_author_photo
            or fallback_photo(feed.origin))

        yield entry


def process_html_feed_for_new_entries(session, feed, response, backfill):
    doc = get_response_content(response)
    parsed = mf2util.interpret_feed(
        mf2py.parse(url=feed.feed, doc=doc), feed.feed)
    hfeed = parsed.get('entries', [])

    for hentry in hfeed:
        entry = hentry_to_entry(hentry, feed, backfill)
        if entry:
            logger.debug('built entry: %s', entry.permalink)
            yield entry


def hentry_to_entry(hentry, feed, backfill):
    now = datetime.datetime.utcnow()
    permalink = url = hentry.get('url')
    uid = hentry.get('uid') or url
    if not uid:
        return

    # hentry = mf2util.interpret(mf2py.Parser(url=url).to_dict(), url)
    # permalink = hentry.get('url') or url
    # uid = hentry.get('uid') or uid

    title = hentry.get('name')
    content = hentry.get('content')
    if not content:
        content = title
        title = None

    published = hentry.get('published')
    updated = hentry.get('updated')

    # retrieved time is now unless we're backfilling old posts
    retrieved = now
    if backfill and published:
        retrieved = published

    entry = Entry(
        uid=uid,
        retrieved=retrieved,
        permalink=permalink,
        published=published,
        updated=updated,
        title=title,
        content=content,
        author_name=hentry.get('author', {}).get('name'),
        author_photo=hentry.get('author', {}).get('photo')
        or (feed and fallback_photo(feed.origin)),
        author_url=hentry.get('author', {}).get('url'))

    for prop in 'in-reply-to', 'like-of', 'repost-of':
        value = hentry.get(prop)
        if value:
            entry.set_property(prop, value)

    return entry


@app.task
def fetch_reply_context(entry_id, in_reply_to):
    with session_scope() as session:
        entry = session.query(Entry).get(entry_id)
        context = session.query(Entry)\
                         .filter_by(permalink=in_reply_to).first()

        if not context:
            logger.info('fetching in-reply-to url: %s', in_reply_to)
            parsed = mf2util.interpret(
                mf2py.Parser(url=proxy_url(in_reply_to)).to_dict(),
                in_reply_to)
            if parsed:
                context = hentry_to_entry(parsed, in_reply_to)

        if context:
            entry.reply_context.append(context)
            session.commit()


def proxy_url(url):
    if Config.TWITTER_AU_KEY and Config.TWITTER_AU_SECRET:
        # swap out the a-u url for twitter urls
        match = TWITTER_RE.match(url)
        if match:
            proxy_url = (
                'https://twitter-activitystreams.appspot.com/@me/@all/@app/{}?'
                .format(match.group(2)) + urllib.parse.urlencode({
                    'format': 'html',
                    'access_token_key': Config.TWITTER_AU_KEY,
                    'access_token_secret': Config.TWITTER_AU_SECRET,
                }))
            logger.debug('proxied twitter url %s', proxy_url)
            return proxy_url
    return url



def fallback_photo(url):
    """Use favatar to find an appropriate photo for any URL"""
    domain = urllib.parse.urlparse(url).netloc
    return 'http://www.google.com/s2/favicons?domain=' + domain


def get_response_content(response):
    """Kartik's trick for handling responses that don't specify their
    encoding. Response.text will guess badly if they don't.
    """
    if 'charset' not in response.headers.get('content-type', ''):
        return response.content
    return response.text
