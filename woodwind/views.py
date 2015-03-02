from . import tasks
from .extensions import db, login_mgr, micropub
from .models import Feed, Entry, User
import flask.ext.login as flask_login
import binascii
import bs4
import datetime
import feedparser
import flask
import mf2py
import mf2util
import requests
import re
import urllib
import cgi

views = flask.Blueprint('views', __name__)


@views.route('/')
def index():
    page = int(flask.request.args.get('page', 1))
    entries = []
    ws_topic = None

    if flask_login.current_user.is_authenticated():
        per_page = flask.current_app.config.get('PER_PAGE', 30)
        offset = (page - 1) * per_page
        entry_query = Entry.query\
                           .join(Entry.feed)\
                           .join(Feed.users)\
                           .filter(User.id == flask_login.current_user.id)

        if 'feed' in flask.request.args:
            feed_hex = flask.request.args.get('feed').encode()
            feed_url = binascii.unhexlify(feed_hex).decode('utf-8')
            feed = Feed.query.filter_by(feed=feed_url).first()
            if not feed:
                flask.abort(404)
            entry_query = entry_query.filter(Feed.feed == feed_url)
            ws_topic = 'feed:{}'.format(feed.id)
        else:
            ws_topic = 'user:{}'.format(flask_login.current_user.id)

        entries = entry_query.order_by(Entry.retrieved.desc())\
                             .offset(offset).limit(per_page).all()

    return flask.render_template('feed.jinja2', entries=entries, page=page,
                                 ws_topic=ws_topic)


@views.route('/install')
def install():
    db.create_all()
    return 'Success!'


@views.route('/feeds')
@flask_login.login_required
def feeds():
    feeds = flask_login.current_user.feeds
    sorted_feeds = sorted(feeds, key=lambda f: f.name and f.name.lower())
    return flask.render_template('feeds.jinja2', feeds=sorted_feeds)


@views.route('/settings', methods=['GET', 'POST'])
@flask_login.login_required
def settings():
    settings = flask_login.current_user.settings or {}
    if flask.request.method == 'GET':
        return flask.render_template('settings.jinja2', settings=settings)

    settings = dict(settings)
    reply_method = flask.request.form.get('reply-method')
    settings['reply-method'] = reply_method

    if reply_method == 'micropub':
        pass
    elif reply_method == 'indie-config':
        settings['indie-config-actions'] = flask.request.form.getlist(
            'indie-config-action')
    elif reply_method == 'action-urls':
        zipped = zip(
            flask.request.form.getlist('action'),
            flask.request.form.getlist('action-url'))
        settings['action-urls'] = [[k, v] for k, v in zipped if k and v]

    flask_login.current_user.settings = settings
    db.session.commit()
    return flask.render_template('settings.jinja2', settings=settings)


@views.route('/update_feed', methods=['POST'])
@flask_login.login_required
def update_feed():
    feed_id = flask.request.form.get('id')
    tasks.update_feed.delay(feed_id)
    return flask.redirect(flask.url_for('.feeds'))


@views.route('/update_all', methods=['POST'])
@flask_login.login_required
def update_all():
    for feed in flask_login.current_user.feeds:
        tasks.update_feed.delay(feed.id)
    return flask.redirect(flask.url_for('.feeds'))


@views.route('/unsubscribe_feed', methods=['POST'])
@flask_login.login_required
def unsubscribe_feed():
    feed_id = flask.request.form.get('id')
    feed = Feed.query.get(feed_id)

    feeds = flask_login.current_user.feeds
    feeds.remove(feed)

    db.session.commit()
    flask.flash('Unsubscribed {} ({})'.format(feed.name, feed.feed))
    return flask.redirect(flask.url_for('.feeds'))


@views.route('/edit_feed', methods=['POST'])
@flask_login.login_required
def edit_feed():
    feed_id = flask.request.form.get('id')
    feed_name = flask.request.form.get('name')
    feed_url = flask.request.form.get('feed')

    feed = Feed.query.get(feed_id)
    if feed_name:
        feed.name = feed_name
    if feed_url:
        feed.feed = feed_url

    db.session.commit()
    flask.flash('Edited {} ({})'.format(feed.name, feed.feed))
    return flask.redirect(flask.url_for('.feeds'))


@views.route('/logout')
def logout():
    flask_login.logout_user()
    return flask.redirect(flask.url_for('.index'))


@views.route('/login', methods=['POST'])
def login():
    return micropub.authenticate(
        flask.request.form.get('me'),
        next_url=flask.request.form.get('next'))


@views.route('/login-callback')
@micropub.authenticated_handler
def login_callback(resp):
    if not resp.me:
        flask.flash(cgi.escape('Login error: ' + resp.error))
        return flask.redirect(flask.url_for('.index'))

    if resp.error:
        flask.flash(cgi.escape('Warning: ' + resp.error))

    domain = urllib.parse.urlparse(resp.me).netloc
    user = load_user(domain)
    if not user:
        user = User()
        user.domain = domain
        db.session.add(user)

    user.url = resp.me
    db.session.commit()
    flask_login.login_user(user, remember=True)
    update_micropub_syndicate_to()
    return flask.redirect(resp.next_url or flask.url_for('.index'))


@views.route('/authorize')
@flask_login.login_required
def authorize():
    return micropub.authorize(
        me=flask_login.current_user.url,
        next_url=flask.request.args.get('next'),
        scope='post')


@views.route('/micropub-callback')
@micropub.authorized_handler
def micropub_callback(resp):
    if not resp.me or resp.error:
        flask.flash(cgi.escape('Authorize error: ' + resp.error))
        return flask.redirect(flask.url_for('.index'))

    domain = urllib.parse.urlparse(resp.me).netloc
    user = load_user(domain)
    if not user:
        flask.flash(cgi.escape('Unknown user for domain: ' + domain))
        return flask.redirect(flask.url_for('.index'))

    user.micropub_endpoint = resp.micropub_endpoint
    user.access_token = resp.access_token
    db.session.commit()
    update_micropub_syndicate_to()
    return flask.redirect(resp.next_url or flask.url_for('.index'))


@flask_login.login_required
def update_micropub_syndicate_to():
    endpt = flask_login.current_user.micropub_endpoint
    token = flask_login.current_user.access_token
    if not endpt or not token:
        return
    resp = requests.get(endpt, params={
        'q': 'syndicate-to',
    }, headers={
        'Authorization': 'Bearer ' + token,
    })
    if resp.status_code // 100 != 2:
        flask.current_app.logger.warn(
            'Unexpected response querying micropub endpoint %s: %s',
            resp, resp.text)
        return
    syndicate_tos = urllib.parse.parse_qs(resp.text).get('syndicate-to[]', [])
    flask_login.current_user.set_setting('syndicate-to', syndicate_tos)
    db.session.commit()


@views.route('/deauthorize')
@flask_login.login_required
def deauthorize():
    flask_login.current_user.micropub_endpoint = None
    flask_login.current_user.access_token = None
    db.session.commit()
    return flask.redirect(flask.request.args.get('next')
                          or flask.url_for('.index'))


@login_mgr.user_loader
def load_user(domain):
    return User.query.filter_by(domain=domain).first()


@views.route('/subscribe', methods=['GET', 'POST'])
@flask_login.login_required
def subscribe():
    if flask.request.method == 'POST':
        origin = flask.request.form.get('origin')
        if origin:
            type = None
            feed = None
            typed_feed = flask.request.form.get('feed')
            if typed_feed:
                type, feed = typed_feed.split('|', 1)
            else:
                feeds = find_possible_feeds(origin)
                if not feeds:
                    flask.flash('No feeds found for: ' + origin)
                    return flask.redirect(flask.url_for('.index'))
                if len(feeds) > 1:
                    return flask.render_template(
                        'select-feed.jinja2', origin=origin, feeds=feeds)
                feed = feeds[0]['feed']
                type = feeds[0]['type']
            new_feed = add_subscription(origin, feed, type)
            flask.flash('Successfully subscribed to: {}'.format(new_feed.name))
            return flask.redirect(flask.url_for('.index'))
        else:
            flask.abort(400)

    return flask.render_template('subscribe.jinja2')


def add_subscription(origin, feed_url, type):
    feed = Feed.query.filter_by(feed=feed_url, type=type).first()
    if not feed:
        if type == 'html':
            flask.current_app.logger.debug('mf2py parsing %s', feed_url)
            parsed = mf2util.interpret_feed(
                mf2py.Parser(url=feed_url).to_dict(), feed_url)
            name = parsed.get('name')
            if not name or len(name) > 140:
                p = urllib.parse.urlparse(origin)
                name = p.netloc + p.path
            feed = Feed(name=name, origin=origin, feed=feed_url, type=type)
        elif type == 'xml':
            flask.current_app.logger.debug('feedparser parsing %s', feed_url)
            parsed = feedparser.parse(feed_url)
            feed = Feed(name=parsed.feed and parsed.feed.title,
                        origin=origin, feed=feed_url, type=type)
    if feed:
        db.session.add(feed)
        flask_login.current_user.feeds.append(feed)
        db.session.commit()
        # go ahead and update the fed
        tasks.update_feed.delay(feed.id)
    return feed


def find_possible_feeds(origin):
    # scrape an origin source to find possible alternative feeds
    resp = requests.get(origin)

    feeds = []

    xml_feed_types = [
        'application/rss+xml',
        'application/atom+xml',
        'application/rdf+xml',
        'application/xml',
    ]
    xml_mime_types = xml_feed_types + [
        'text/xml',
        'text/rss+xml',
        'text/atom+xml',
    ]

    content_type = resp.headers['content-type']
    content_type = content_type.split(';', 1)[0].strip()
    if content_type in xml_mime_types:
        feeds.append({
            'origin': origin,
            'feed': origin,
            'type': 'xml',
        })

    elif content_type == 'text/html':
        # if text/html, then parse and look for h-entries
        hfeed = mf2util.interpret_feed(
            mf2py.Parser(doc=resp.text).to_dict(), origin)
        if hfeed.get('entries'):
            feeds.append({
                'origin': origin,
                'feed': origin,
                'type': 'html',
            })

        # then look for link rel="alternate"
        soup = bs4.BeautifulSoup(resp.text)
        for link in soup.find_all('link', {'rel': 'alternate'}):
            if link.get('type') in xml_feed_types:
                feed_url = urllib.parse.urljoin(origin, link.get('href'))
                feeds.append({
                    'origin': origin,
                    'feed': feed_url,
                    'type': 'xml',
                })
    return feeds


@views.app_template_filter()
def prettify_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.path:
        return parsed.netloc + parsed.path
    return parsed.netloc


@views.app_template_filter()
def domain_for_url(url):
    parsed = urllib.parse.urlparse(url)
    return parsed.netloc


@views.app_template_filter()
def favicon_for_url(url):
    parsed = urllib.parse.urlparse(url)
    return 'http://www.google.com/s2/favicons?domain={}'.format(parsed.netloc)


@views.app_template_filter()
def relative_time(dt):
    if dt:
        now = datetime.datetime.utcnow()
        diff = now - dt
        zero = datetime.timedelta(0)
        years = diff.days // 365
        hours = diff.seconds // 60 // 60
        minutes = diff.seconds // 60

        if diff == zero:
            pretty = 'Right now'
        if diff > zero:
            if years > 1:
                pretty = str(years) + ' years ago'
            elif diff.days == 1:
                pretty = 'A day ago'
            elif diff.days > 1:
                pretty = str(diff.days) + ' days ago'
            elif hours == 1:
                pretty = 'An hour ago'
            elif hours > 1:
                pretty = str(hours) + ' hours ago'
            elif minutes == 1:
                pretty = 'A minute ago'
            elif minutes > 1:
                pretty = str(minutes) + ' minutes ago'
            else:
                pretty = str(diff.seconds) + ' seconds ago'
        else:
            if years < -1:
                pretty = str(-years) + ' years from now'
            elif diff.days == -1:
                pretty = 'A day from now'
            elif diff.days < -1:
                pretty = str(-diff.days) + ' days from now'
            elif hours == -1:
                pretty = 'An hour from now'
            elif hours < -1:
                pretty = str(-hours) + ' hours from now'
            elif minutes == -1:
                pretty = 'A minute from now'
            elif minutes < -1:
                pretty = str(-minutes) + ' minutes from now'
            else:
                pretty = str(-diff.seconds) + ' seconds from now'

        return '<time datetime="{}">{}</time>'.format(dt.isoformat(), pretty)


@views.app_template_filter()
def isoformat(dt):
    return dt and dt.isoformat()


@views.app_template_filter()
def add_preview(content):
    """If a post ends with the URL of a known media source (youtube,
    instagram, etc.), add the content inline.
    """
    if any('<' + tag in content for tag in (
            'img', 'iframe', 'embed', 'audio', 'video')):
        # don't add  a preview to a post that already has one
        return content

    instagram_regex = 'https?://instagram.com/p/[\w\-]+/?'
    vimeo_regex = 'https?://vimeo.com/(\d+)/?'
    youtube_regex = 'https?://(?:www.)youtube.com/watch\?v=([\w\-]+)'

    m = re.search(instagram_regex, content)
    if m:
        ig_url = m.group(0)
        media_url = urllib.parse.urljoin(ig_url, 'media/?size=l')
        return '{}<a href="{}"><img src="{}" /></a>'.format(
            content, ig_url, media_url)

    m = re.search(vimeo_regex, content)
    if m:
        # vimeo_url = m.group(0)
        vimeo_id = m.group(1)
        return (
            '{}<iframe src="//player.vimeo.com/video/{}" width="560" '
            'height="315" frameborder="0" webkitallowfullscreen '
            'mozallowfullscreen allowfullscreen></iframe>'
        ).format(content, vimeo_id)

    m = re.search(youtube_regex, content)
    if m:
        youtube_id = m.group(1)
        return (
            '{}<iframe width="560" height="315" '
            'src="https://www.youtube.com/embed/{}" frameborder="0" '
            'allowfullscreen></iframe>'
        ).format(content, youtube_id)

    return content


@views.app_template_global()
def url_for_other_page(page):
    """http://flask.pocoo.org/snippets/44/#URL+Generation+Helper
    """
    args = flask.request.view_args.copy()
    args.update(flask.request.args)
    args['page'] = page

    return flask.url_for(flask.request.endpoint, **args)
