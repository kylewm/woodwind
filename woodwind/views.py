from . import tasks
from .extensions import db, login_mgr, micropub
from .models import Feed, Entry, User, Subscription
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
import sqlalchemy

views = flask.Blueprint('views', __name__)


@views.route('/')
def index():
    page = int(flask.request.args.get('page', 1))
    entry_tups = []
    ws_topic = None
    solo = False
    all_tags = set()

    if flask_login.current_user.is_authenticated():
        for subsc in flask_login.current_user.subscriptions:
            if subsc.tags:
                all_tags.update(subsc.tags.split())

        per_page = flask.current_app.config.get('PER_PAGE', 30)
        offset = (page - 1) * per_page

        entry_query = db.session.query(Entry, Subscription)\
            .options(
                sqlalchemy.orm.subqueryload(Entry.feed),
                sqlalchemy.orm.subqueryload(Entry.reply_context)
            )\
            .join(Entry.feed)\
            .join(Feed.subscriptions)\
            .join(Subscription.user)\
            .filter(User.id == flask_login.current_user.id)

        if 'entry' in flask.request.args:
            entry_url = flask.request.args.get('entry')
            entry_tup = entry_query.filter(Entry.permalink == entry_url)\
                                   .order_by(Entry.retrieved.desc())\
                                   .first()
            if not entry_tup:
                flask.abort(404)
            entry_tups = [entry_tup]
            solo = True
        else:
            if 'tag' in flask.request.args:
                tag = flask.request.args.get('tag')
                entry_query = entry_query.filter(
                    Subscription.tags.like('%{}%'.format(tag)))
            elif 'subscription' in flask.request.args:
                subsc_id = flask.request.args.get('subscription')
                subsc = Subscription.query.get(subsc_id)
                if not subsc:
                    flask.abort(404)
                entry_query = entry_query.filter(Subscription.id == subsc_id)
                ws_topic = 'subsc:{}'.format(subsc.id)
            else:
                ws_topic = 'user:{}'.format(flask_login.current_user.id)

            entry_query = entry_query.order_by(Entry.retrieved.desc(),
                                               Entry.published.desc())\
                                     .offset(offset).limit(per_page)
            print('found some entries:', len(entry_query.all()))
            entry_tups = entry_query.all()

    # stick the subscription into the entry.
    # FIXME this is hacky
    entries = []
    for entry, subsc in entry_tups:
        entry.subscription = subsc
        entries.append(entry)

    entries = dedupe_copies(entries)
    return flask.render_template('feed.jinja2', entries=entries, page=page,
                                 ws_topic=ws_topic, solo=solo,
                                 all_tags=all_tags)


@views.route('/install')
def install():
    db.create_all()
    return 'Success!'


@views.route('/subscriptions')
@flask_login.login_required
def subscriptions():
    subscs = Subscription\
        .query\
        .filter_by(user_id=flask_login.current_user.id)\
        .options(sqlalchemy.orm.subqueryload(Subscription.feed))\
        .order_by(db.func.lower(Subscription.name))\
        .all()

    return flask.render_template('subscriptions.jinja2',
                                 subscriptions=subscs)


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
    tasks.q.enqueue(tasks.update_feed, feed_id)
    return flask.redirect(flask.url_for('.subscriptions'))


@views.route('/update_all', methods=['POST'])
@flask_login.login_required
def update_all():
    for s in flask_login.current_user.subscriptions:
        tasks.q.enqueue(tasks.update_feed, s.feed.id)
    return flask.redirect(flask.url_for('.subscriptions'))


@views.route('/unsubscribe', methods=['POST'])
@flask_login.login_required
def unsubscribe():
    subsc_id = flask.request.form.get('id')
    subsc = Subscription.query.get(subsc_id)
    db.session.delete(subsc)
    db.session.commit()
    flask.flash('Unsubscribed {}'.format(subsc.name))
    return flask.redirect(flask.url_for('.subscriptions'))


@views.route('/edit_subscription', methods=['POST'])
@flask_login.login_required
def edit_subscription():
    subsc_id = flask.request.form.get('id')
    subsc_name = flask.request.form.get('name')
    subsc_tags = flask.request.form.get('tags')

    subsc = Subscription.query.get(subsc_id)
    if subsc_name:
        subsc.name = subsc_name
    if subsc_tags:
        tag_list = re.split(r'(?:\s|,)+', subsc_tags)
        subsc.tags = ' '.join(t.strip() for t in tag_list if t.strip())
    else:
        subsc.tags = None

    db.session.commit()
    flask.flash('Edited {}'.format(subsc.name))
    return flask.redirect(flask.url_for('.subscriptions'))


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


def add_subscription(origin, feed_url, type, tags=None):
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

        flask_login.current_user.subscriptions.append(
            Subscription(feed=feed, name=feed.name, tags=tags))

        db.session.commit()
        # go ahead and update the fed
        tasks.q.enqueue(tasks.update_feed, feed.id)
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
        parsed = mf2py.parse(doc=resp.text, url=origin)
        # if text/html, then parse and look for h-entries
        hfeed = mf2util.interpret_feed(parsed, origin)
        if hfeed.get('entries'):
            feeds.append({
                'origin': origin,
                'feed': resp.url,
                'type': 'html',
            })

        # then look for link rel="alternate"
        for link in parsed.get('alternates', []):
            if link.get('type') in xml_feed_types:
                feeds.append({
                    'origin': origin,
                    'feed': link.get('url'),
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
    return '//www.google.com/s2/favicons?domain={}'.format(parsed.netloc)


@views.app_template_filter()
def relative_time(dt):
    if dt:
        now = datetime.datetime.utcnow()
        diff = now - dt
        zero = datetime.timedelta(0)

        if diff == zero:
            pretty = 'Right now'
        elif diff > zero:
            years = diff.days // 365
            hours = diff.seconds // 60 // 60
            minutes = diff.seconds // 60

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
            diff = abs(diff)
            years = diff.days // 365
            hours = diff.seconds // 60 // 60
            minutes = diff.seconds // 60

            if years > 1:
                pretty = str(years) + ' years from now'
            elif diff.days == 1:
                pretty = 'A day from now'
            elif diff.days > 1:
                pretty = str(diff.days) + ' days from now'
            elif hours == 1:
                pretty = 'An hour from now'
            elif hours > 1:
                pretty = str(hours) + ' hours from now'
            elif minutes == 1:
                pretty = 'A minute from now'
            elif minutes > 1:
                pretty = str(minutes) + ' minutes from now'
            else:
                pretty = str(diff.seconds) + ' seconds from now'

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


def dedupe_copies(entries):
    all_copies = set()
    for entry in entries:
        syndurls = entry.get_property('syndication')
        if syndurls:
            copies = [e for e in entries if e.permalink in syndurls]
            entry._syndicated_copies = copies
            all_copies.update(copies)
    return [e for e in entries if e not in all_copies]
