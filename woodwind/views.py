from . import tasks, util
from .extensions import db, login_mgr, micropub
from .models import Feed, Entry, User, Subscription
import flask.ext.login as flask_login

import base64
import bs4
import datetime
import feedparser
import flask
import hashlib
import hmac
import mf2py
import mf2util
import pyquerystring
import requests
import re
import urllib
import cgi
import sqlalchemy
import sqlalchemy.sql.expression

IMAGE_TAG_RE = re.compile(r'<img([^>]*) src="(https?://[^">]+)"')


views = flask.Blueprint('views', __name__)


@views.route('/')
def index():
    page = int(flask.request.args.get('page', 1))
    entry_tups = []
    ws_topic = None
    solo = False
    all_tags = set()

    if flask_login.current_user.is_authenticated:
        for subsc in flask_login.current_user.subscriptions:
            if subsc.tags:
                all_tags.update(subsc.tags.split())

        per_page = flask.current_app.config.get('PER_PAGE', 30)
        offset = (page - 1) * per_page

        entry_query = db.session.query(Entry, Subscription)\
            .options(
                sqlalchemy.orm.subqueryload(Entry.feed),
                sqlalchemy.orm.subqueryload(Entry.reply_context))\
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
            elif 'jam' in flask.request.args:
                entry_query = entry_query.filter(
                    sqlalchemy.sql.expression.cast(Entry.properties['jam'], sqlalchemy.TEXT) == 'true')
            else:
                entry_query = entry_query.filter(Subscription.exclude == False)
                ws_topic = 'user:{}'.format(flask_login.current_user.id)

            entry_query = entry_query.order_by(Entry.retrieved.desc(),
                                               Entry.published.desc())\
                                     .offset(offset).limit(per_page)
            entry_tups = entry_query.all()

    # stick the subscription into the entry.
    # FIXME this is hacky
    entries = []
    for entry, subsc in entry_tups:
        entry.subscription = subsc
        entries.append(entry)

    entries = dedupe_copies(entries)
    resp = flask.make_response(
        flask.render_template('feed.jinja2', entries=entries, page=page,
                              ws_topic=ws_topic, solo=solo,
                              all_tags=all_tags))
    resp.headers['Cache-control'] = 'max-age=0'
    return resp


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
    flask_login.current_user.settings = settings
    db.session.commit()

    next_page = '.settings'
    if reply_method == 'micropub':
        next_page = '.settings_micropub'
    elif reply_method == 'indie-config':
        next_page = '.settings_indie_config'
    elif reply_method == 'action-urls':
        next_page = '.settings_action_urls'

    return flask.redirect(flask.url_for(next_page))


@views.route('/settings/micropub')
@flask_login.login_required
def settings_micropub():
    settings = flask_login.current_user.settings or {}
    return flask.render_template('settings_micropub.jinja2', settings=settings)


@views.route('/settings/indie-config', methods=['GET', 'POST'])
@flask_login.login_required
def settings_indie_config():
    settings = flask_login.current_user.settings or {}

    if flask.request.method == 'GET':
        return flask.render_template('settings_indie_config.jinja2',
                                     settings=settings)

    settings = dict(settings)
    settings['indie-config-actions'] = flask.request.form.getlist(
        'indie-config-action')
    flask_login.current_user.settings = settings
    print('new settings: ', settings)
    db.session.commit()
    return flask.redirect(flask.url_for('.index'))


@views.route('/settings/action-urls', methods=['GET', 'POST'])
@flask_login.login_required
def settings_action_urls():
    settings = flask_login.current_user.settings or {}
    if flask.request.method == 'GET':
        return flask.render_template('settings_action_urls.jinja2',
                                     settings=settings)

    settings = dict(settings)
    zipped = zip(
        flask.request.form.getlist('action'),
        flask.request.form.getlist('action-url'))
    settings['action-urls'] = [[k, v] for k, v in zipped if k and v]
    flask_login.current_user.settings = settings
    db.session.commit()
    return flask.redirect(flask.url_for('.index'))


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
    subsc.exclude = flask.request.form.get('exclude') == 'true'

    db.session.commit()
    flask.flash('Edited {}'.format(subsc.name))
    return flask.redirect(flask.url_for('.subscriptions'))


@views.route('/logout')
def logout():
    flask_login.logout_user()
    return flask.redirect(flask.url_for('.index'))


@views.route('/login', methods=['POST'])
def login():
    me = flask.request.form.get('me')
    if not me or me == 'http://':
        flask.flash('Sign in with your personal web address.')
        return flask.redirect(flask.url_for('.index'))

    return micropub.authenticate(
        me=me, next_url=flask.request.form.get('next'))


@views.route('/login-callback')
@micropub.authenticated_handler
def login_callback(resp):
    if not resp.me:
        flask.flash(cgi.escape('Login error: ' + resp.error))
        return flask.redirect(flask.url_for('.index'))

    if resp.error:
        flask.flash(cgi.escape('Warning: ' + resp.error))

    user = load_user(resp.me)
    if not user:
        user = User(url=resp.me)
        db.session.add(user)

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

    user = load_user(resp.me)
    if not user:
        flask.flash(cgi.escape('Unknown user for url: ' + resp.me))
        return flask.redirect(flask.url_for('.index'))

    user.micropub_endpoint = resp.micropub_endpoint
    user.access_token = resp.access_token
    db.session.commit()
    update_micropub_syndicate_to()

    flask.flash('Logged in as ' + user.url)
    return flask.redirect(resp.next_url or flask.url_for('.index'))


@flask_login.login_required
def update_micropub_syndicate_to():

    def adapt_expanded(exp):
        """Backcompat support for old-style "syndicate-to-expanded" properties,
        e.g.,
        {
          "id": "twitter::kylewmahan",
          "name": "@kylewmahan",
          "service": "Twitter"
        }
        """
        if isinstance(exp, dict):
            return {
                'uid': exp.get('id'),
                'name': '{} on {}'.format(exp.get('name'), exp.get('service')),
            }
        return exp

    endpt = flask_login.current_user.micropub_endpoint
    token = flask_login.current_user.access_token
    if not endpt or not token:
        return
    resp = util.requests_get(endpt, params={
        'q': 'syndicate-to',
    }, headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/json',
    })
    if resp.status_code // 100 != 2:
        flask.current_app.logger.warn(
            'Unexpected response querying micropub endpoint %s: %s',
            resp, resp.text)
        return

    flask.current_app.logger.debug('syndicate-to response: {}, {}',
                                   resp, resp.text)

    content_type = resp.headers['content-type']
    if content_type:
        content_type = content_type.split(';', 1)[0]

    if content_type == 'application/json':
        blob = resp.json()
        syndicate_tos = adapt_expanded(blob.get('syndicate-to-expanded'))
        if not syndicate_tos:
            syndicate_tos = blob.get('syndicate-to')

    else:  # try to parse query string
        syndicate_tos = pyquerystring.parse(resp.text).get('syndicate-to', [])
        if isinstance(syndicate_tos, list):
            syndicate_tos = list(syndicate_tos)

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
def load_user(url):
    alt = url.rstrip('/') if url.endswith('/') else url + '/'
    return User.query.filter(
        (User.url == url) | (User.url == alt)).first()


@views.route('/subscribe', methods=['GET', 'POST'])
@flask_login.login_required
def subscribe():
    origin = (flask.request.form.get('origin')
              or flask.request.args.get('origin'))
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

    if flask.request.method == 'POST':
        flask.abort(400)

    return flask.render_template('subscribe.jinja2')


def add_subscription(origin, feed_url, type, tags=None):
    feed = Feed.query.filter_by(feed=feed_url, type=type).first()

    if not feed:
        name = None
        if type == 'html':
            flask.current_app.logger.debug('mf2py parsing %s', feed_url)
            resp = util.requests_get(feed_url)
            feed_text = resp.text if 'charset' in resp.headers.get('content-type', '') else resp.content
            parsed = mf2util.interpret_feed(
                mf2py.parse(doc=feed_text, url=feed_url), feed_url)
            name = parsed.get('name')
        elif type == 'xml':
            flask.current_app.logger.debug('feedparser parsing %s', feed_url)
            parsed = feedparser.parse(feed_url, agent=util.USER_AGENT)
            if parsed.feed:
                name = parsed.feed.get('title')
        else:
            flask.current_app.logger.error('unknown feed type %s', type)
            flask.abort(400)

        if not name:
            p = urllib.parse.urlparse(origin)
            name = p.netloc + p.path
        feed = Feed(name=name[:140], origin=origin, feed=feed_url, type=type)

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
    try:
        resp = util.requests_get(origin)
    except requests.exceptions.RequestException as e:
        flask.flash('Error fetching source {}'.format(repr(e)))
        flask.current_app.logger.warn(
            'Subscribe failed for %s with error %s', origin, repr(e))
        return None

    feeds = []

    xml_feed_types = [
        'application/rss+xml',
        'application/atom+xml',
        'application/rdf+xml',
        'application/xml',
        'text/xml',
    ]
    xml_mime_types = xml_feed_types + [
        'text/xml',
        'text/rss+xml',
        'text/atom+xml',
    ]
    html_feed_types = [
        'text/html',
        'application/xhtml+xml',
    ]

    content_type = resp.headers['content-type']
    content_type = content_type.split(';', 1)[0].strip()
    if content_type in xml_mime_types:
        feeds.append({
            'origin': origin,
            'feed': origin,
            'type': 'xml',
            'title': 'untitled xml feed',
        })

    elif content_type in html_feed_types:
        parsed = mf2py.parse(doc=resp.text, url=origin)
        # if text/html, then parse and look for h-entries
        hfeed = mf2util.interpret_feed(parsed, origin)
        if hfeed.get('entries'):
            ftitle = hfeed.get('name') or 'untitled h-feed'
            feeds.append({
                'origin': origin,
                'feed': resp.url,
                'type': 'html',
                'title': ftitle[:140]
            })

        # look for link="feed"
        for furl in parsed.get('rels', {}).get('feed', []):
            fprops = parsed.get('rel-urls', {}).get(furl, {})
            if not fprops.get('type') or fprops.get('type') in html_feed_types:
                feeds.append({
                    'origin': origin,
                    'feed': furl,
                    'type': 'html',
                    'title': fprops.get('title'),
                })

        # then look for link rel="alternate"
        for link in parsed.get('alternates', []):
            if link.get('type') in xml_feed_types:
                feeds.append({
                    'origin': origin,
                    'feed': link.get('url'),
                    'type': 'xml',
                    'title': link.get('title'),
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
    return '//www.google.com/s2/favicons?' + urllib.parse.urlencode({
        'domain': url,
    })


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
    if not content or any('<' + tag in content for tag in (
            'img', 'iframe', 'embed', 'audio', 'video')):
        # don't add  a preview to a post that already has one
        return content

    # flatten links and strip tags
    flat = content
    flat = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>[^<]*</a>', r'\1', flat)
    flat = re.sub(r'</?\w+[^>]*>', '', flat)
    flat = flat.strip()

    instagram_regex = r'https?://(?:www\.)?instagram.com/p/[\w\-]+/?'
    vimeo_regex = r'https?://(?:www\.)?vimeo.com/(\d+)/?'
    youtube_regex = r'https?://(?:www\.)?youtube.com/watch\?v=([\w\-]+)'
    youtube_short_regex = r'https://youtu.be/([\w\-]+)'
    twitter_regex = r'https?://(?:www\.)?twitter.com/(\w+)/status/(\d+)'

    m = re.search(instagram_regex, flat)
    if m:
        ig_url = m.group(0)
        media_url = urllib.parse.urljoin(ig_url, 'media/?size=l')
        return '{}<a href="{}"><img src="{}" /></a>'.format(
            content, ig_url, media_url)

    m = re.search(vimeo_regex, flat)
    if m:
        # vimeo_url = m.group(0)
        vimeo_id = m.group(1)
        return (
            '{}<iframe src="//player.vimeo.com/video/{}" width="560" '
            'height="315" frameborder="0" webkitallowfullscreen '
            'mozallowfullscreen allowfullscreen></iframe>'
        ).format(content, vimeo_id)

    m = re.search(youtube_regex, flat)
    if not m:
        m = re.search(youtube_short_regex, content)

    if m:
        youtube_id = m.group(1)
        return (
            '{}<iframe width="560" height="315" '
            'src="https://www.youtube.com/embed/{}" frameborder="0" '
            'allowfullscreen></iframe>'
        ).format(content, youtube_id)

    m = re.search(twitter_regex + '$', flat)
    if m:
        tweet_url = m.group()
        return content + (
            '<blockquote class="twitter-tweet" lang="en" data-cards="hidden">'
            '<a href="{}"></a></blockquote>'
        ).format(tweet_url)

    return content


@views.app_template_filter()
def proxy_image(url):
    proxy_url = flask.current_app.config.get('IMAGEPROXY_URL')
    proxy_key = flask.current_app.config.get('IMAGEPROXY_KEY')
    if proxy_url and proxy_key:
        sig = base64.urlsafe_b64encode(
            hmac.new(proxy_key.encode(), url.encode(), hashlib.sha256).digest()
        ).decode()
        return '/'.join((proxy_url.rstrip('/'), 's' + sig, url))

    pilbox_url = flask.current_app.config.get('PILBOX_URL')
    pilbox_key = flask.current_app.config.get('PILBOX_KEY')
    if pilbox_url and pilbox_key:
        query = urllib.parse.urlencode({'url': url, 'op': 'noop'})
        sig = hmac.new(pilbox_key.encode(), query.encode(), hashlib.sha1).hexdigest()
        query += '&sig=' + sig
        return pilbox_url + '?' + query

    camo_url = flask.current_app.config.get('CAMO_URL')
    camo_key = flask.current_app.config.get('CAMO_KEY')
    if camo_url and camo_key:
        digest = hmac.new(camo_key.encode(), url.encode(), hashlib.sha1).hexdigest()
        return (urllib.parse.urljoin(camo_url, digest)
                + '?url=' + urllib.parse.quote_plus(url))
    return url


@views.app_template_filter()
def proxy_all(content):
    def repl(m):
        attrs = m.group(1)
        url = m.group(2)
        url = url.replace('&amp;', '&')
        return '<img{} src="{}"'.format(attrs, proxy_image(url))
    if content:
        return IMAGE_TAG_RE.sub(repl, content)


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


def font_awesome_class_for_service(service):
    service = service.lower()
    if service == 'facebook':
        return 'fa fa-facebook'
    if service == 'twitter':
        return 'fa fa-twitter'
    if service == 'instagram':
        return 'fa fa-instagram'
    if service == 'flickr':
        return 'fa fa-flickr'
    if service == 'googleplus' or service == 'g+' or service == 'google plus' or service == 'google+':
        return 'fa fa-google-plus'
    if service == 'hacker news' or service == 'hackernews':
        return 'fa fa-hacker-news'
    if service == 'indienews':
        return 'fa fa-newspaper-o'
    if service == 'linkedin':
        return 'fa fa-linkedin'
    if service == 'foursquare' or service == 'swarm':
        return 'fa fa-foursquare'
    return 'fa fa-send'


@views.app_template_filter('syndication_target_id')
def syndication_target_id(target):
    if isinstance(target, dict):
        return target.get('uid') or target.get('id')
    return target


@views.app_template_filter('render_syndication_target')
def render_syndication_target(target):
    if isinstance(target, dict):
        full_name = target.get('name')
        return full_name

    return '<img src="{}" alt="{}" />&nbsp;{}'.format(
        favicon_for_url(target), target, prettify_url(target))


@views.app_template_test('syndicated_to')
def is_syndicated_to(entry, target):
    def same_domain(u1, u2):
        return domain_for_url(u1) == domain_for_url(u2)

    if isinstance(target, dict):
        return False  # TODO

    return same_domain(entry.permalink, target) or any(
        same_domain(syndurl, target)
        for syndurl in entry.get_property('syndication', []))
