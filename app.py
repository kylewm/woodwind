from config import Config
from flask.ext.login import LoginManager
from flask.ext.micropub import MicropubClient
from flask.ext.sqlalchemy import SQLAlchemy
import bleach
import bs4
import datetime
import feedparser
import flask
import flask.ext.login as flask_login
import itertools
import mf2py
import mf2util
import requests
import time
import urllib.parse


app = flask.Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
micropub = MicropubClient(app, client_id='redwind-reader')
login_mgr = LoginManager(app)
login_mgr.login_view = 'login'


bleach.ALLOWED_TAGS += ['a', 'img', 'p', 'br', 'marquee', 'blink']
bleach.ALLOWED_ATTRIBUTES.update({
    'img': ['src', 'alt', 'title']
})


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(256))
    micropub_endpoint = db.Column(db.String(512))
    access_token = db.Column(db.String(512))

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.domain

    def __eq__(self, other):
        if type(other) is type(self):
            return self.domain == other.domain
        return False

    def __repr__(self):
        return '<User:{}>'.format(self.domain)


class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    user = db.relationship(User, backref='feeds')
    # the name of this feed
    name = db.Column(db.String(256))
    # url that we subscribed to; periodically check if the feed url
    # has changed
    origin = db.Column(db.String(512))
    # url of the feed itself
    feed = db.Column(db.String(512))
    # h-feed, xml, etc.
    type = db.Column(db.String(64))
    # last time this feed returned new data
    last_updated = db.Column(db.DateTime)
    # last time we checked this feed
    last_checked = db.Column(db.DateTime)
    etag = db.Column(db.String(512))

    def __repr__(self):
        return '<Feed:{},{}>'.format(self.name, self.feed)


class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    feed_id = db.Column(db.Integer, db.ForeignKey(Feed.id))
    feed = db.relationship(Feed, backref='entries')
    published = db.Column(db.DateTime)
    updated = db.Column(db.DateTime)
    retrieved = db.Column(db.DateTime)
    uid = db.Column(db.String(512))
    permalink = db.Column(db.String(512))
    author_name = db.Column(db.String(512))
    author_url = db.Column(db.String(512))
    author_photo = db.Column(db.String(512))
    title = db.Column(db.String(512))
    content = db.Column(db.Text)

    def content_cleaned(self):
        if self.content:
            return bleach.clean(self.content, strip=True)

    def __repr__(self):
        return '<Entry:{},{}>'.format(self.title, (self.content or '')[:140])


@app.route('/')
def index():
    if flask_login.current_user.is_authenticated():
        feed_ids = [f.id for f in flask_login.current_user.feeds]
        entries = Entry.query.filter(
            Entry.feed_id.in_(feed_ids)).order_by(
                Entry.published.desc()).limit(100).all()
    else:
        entries = []
    return flask.render_template('feed.jinja2', entries=entries)


@app.route('/install')
def install():
    db.drop_all()
    db.create_all()

    user = User(domain='kylewm.com',)
    db.session.add(user)
    db.session.commit()

    flask_login.login_user(user)

    return 'Success!'


def process_feed_for_new_entries(feed):
    if feed.type == 'xml':
        return process_xml_feed_for_new_entries(feed)
    elif feed.type == 'html':
        return process_html_feed_for_new_entries(feed)


def process_xml_feed_for_new_entries(feed):
    app.logger.debug('updating feed: %s', feed)

    now = datetime.datetime.utcnow()
    parsed = feedparser.parse(feed.feed)

    feed_props = parsed.get('feed', {})
    default_author_url = feed_props.get('author_detail', {}).get('href')
    default_author_name = feed_props.get('author_detail', {}).get('name')
    default_author_photo = feed_props.get('logo')

    all_uids = [e.id or e.link for e in parsed.entries]
    preexisting = set(row[0] for row in db.session.query(Entry.uid)
                      .filter(Entry.uid.in_(all_uids))
                      .filter(Entry.feed == feed))

    for p_entry in parsed.entries:
        permalink = p_entry.link
        uid = p_entry.id or permalink

        if not uid or uid in preexisting:
            continue

        updated = datetime.datetime.fromtimestamp(
            time.mktime(p_entry.updated_parsed)
        ) if p_entry.updated_parsed else None
        published = datetime.datetime.fromtimestamp(
            time.mktime(p_entry.published_parsed)
        ) if p_entry.published_parsed else None

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
            feed=feed,
            published=published,
            updated=updated,
            uid=uid,
            permalink=permalink,
            retrieved=now,
            title=p_entry.get('title'),
            content=content,
            author_name=p_entry.get('author_detail', {}).get('name')
            or default_author_name,
            author_url=p_entry.get('author_detail', {}).get('href')
            or default_author_url,
            author_photo=default_author_photo)

        db.session.add(entry)
        db.session.commit()
        yield entry


def process_html_feed_for_new_entries(feed):
    app.logger.debug('updating feed: %s', feed)

    now = datetime.datetime.utcnow()
    parsed = mf2util.interpret_feed(
        mf2py.parse(url=feed.feed), feed.feed)
    hfeed = parsed.get('entries', [])

    all_uids = [e.get('uid') or e.get('url') for e in hfeed]
    preexisting = set(row[0] for row in db.session.query(Entry.uid)
                      .filter(Entry.uid.in_(all_uids))
                      .filter(Entry.feed == feed))

    # app.logger.debug('preexisting urls: %r', preexisting)

    for hentry in hfeed:
        permalink = url = hentry.get('url')
        uid = hentry.get('uid') or url

        if not uid or uid in preexisting:
            continue

        # hentry = mf2util.interpret(mf2py.parse(url=url), url)
        # permalink = hentry.get('url') or url
        # uid = hentry.get('uid') or uid
        entry = Entry(
            feed=feed,
            published=hentry.get('published'),
            updated=hentry.get('updated'),
            uid=uid,
            permalink=permalink,
            retrieved=now,
            title=hentry.get('name'),
            content=hentry.get('content'),
            author_name=hentry.get('author', {}).get('name'),
            author_photo=hentry.get('author', {}).get('photo'),
            author_url=hentry.get('author', {}).get('url'))
        db.session.add(entry)
        db.session.commit()
        app.logger.debug('saved entry: %s', entry.permalink)
        yield entry


@app.route('/update')
def update():
    new_urls = []
    for feed in Feed.query.all():
        new_entries = process_feed_for_new_entries(feed)
        for entry in new_entries:
            new_urls.append(entry.permalink)
    return ('Success!<ul>' + '\n'.join(
        '<li>' + url + '</li>' for url in new_urls) + '</ul>')


@app.route('/login')
def login():
    if True:
        flask_login.login_user(User.query.all()[0], remember=True)

    me = flask.request.args.get('me')
    if me:
        return micropub.authorize(
            me, flask.url_for('login_callback', _external=True),
            next_url=flask.request.args.get('next'),
            scope='write')
    return flask.render_template('login.jinja2')


@app.route('/login-callback')
@micropub.authorized_handler
def login_callback(resp):
    if not resp.me:
        flask.flash('Login error: ' + resp.error)
        return flask.redirect(flask.url_for('login'))

    domain = urllib.parse.urlparse(resp.me).netloc
    user = load_user(domain)
    if not user:
        user = User()
        user.domain = domain
        db.session.add(user)

    user.micropub_endpoint = resp.micropub_endpoint
    user.access_token = resp.access_token
    db.session.commit()

    flask_login.login_user(user, remember=True)
    return flask.redirect(resp.next_url or flask.url_for('index'))


@login_mgr.user_loader
def load_user(domain):
    return User.query.filter_by(domain=domain).first()


@app.route('/subscribe', methods=['GET', 'POST'])
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
                    return flask.redirect(flask.url_for('subscribe'))
                if len(feeds) > 1:
                    return flask.render_template(
                        'select-feed.jinja2', origin=origin, feeds=feeds)
                feed = feeds[0]['feed']
                type = feeds[0]['type']
            new_feed = add_subscription(origin, feed, type)
            flask.flash('Successfully subscribed to: {}'.format(new_feed.name))
            return flask.redirect(flask.url_for('index'))
        else:
            flask.abort(400)

    return flask.render_template('subscribe.jinja2')


def add_subscription(origin, feed, type):
    if type == 'html':
        parsed = mf2util.interpret_feed(mf2py.parse(url=feed), feed)
        name = parsed.get('name')
        if not name or len(name) > 140:
            p = urllib.parse.urlparse(origin)
            name = p.netloc + p.path

        feed = Feed(user=flask_login.current_user, name=name,
                    origin=origin, feed=feed, type=type)

        db.session.add(feed)
        db.session.commit()
        return feed

    elif type == 'xml':
        parsed = feedparser.parse(feed)
        feed = Feed(user=flask_login.current_user,
                    name=parsed.feed.title, origin=origin, feed=feed,
                    type=type)

        db.session.add(feed)
        db.session.commit()
        return feed


def find_possible_feeds(origin):
    # scrape an origin source to find possible alternative feeds
    resp = requests.get(origin)

    feeds = []
    xml_feed_types = [
        'application/rss+xml',
        'application/atom+xml',
        'application/rdf+xml',
    ]

    content_type = resp.headers['content-type']
    content_type = content_type.split(';', 1)[0].strip()
    if content_type in xml_feed_types:
        feeds.append({
            'origin': origin,
            'feed': origin,
            'type': 'xml',
        })

    elif content_type == 'text/html':
        # if text/html, then parse and look for rel="alternate"
        soup = bs4.BeautifulSoup(resp.text)
        for link in soup.find_all('link', {'rel': 'alternate'}):
            if link.get('type') in xml_feed_types:
                feeds.append({
                    'origin': origin,
                    'feed': link.get('href'),
                    'type': 'xml',
                })
        feeds.append({
            'origin': origin,
            'feed': origin,
            'type': 'html',
        })

    return feeds


if __name__ == '__main__':
    app.run(debug=True, port=4000)
