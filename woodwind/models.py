import bleach
import json
from .extensions import db


bleach.ALLOWED_TAGS += ['a', 'img', 'p', 'br', 'marquee', 'blink',
                        'audio', 'video', 'table', 'tbody', 'td', 'tr']
bleach.ALLOWED_ATTRIBUTES.update({
    'img': ['src', 'alt', 'title'],
    'audio': ['preload', 'controls', 'src'],
    'video': ['preload', 'controls', 'src'],
    'td': ['colspan'],
})


class JsonType(db.TypeDecorator):
    """Represents an immutable structure as a json-encoded string.
    http://docs.sqlalchemy.org/en/rel_0_9/core/types.html#marshal-json-strings
    """
    impl = db.Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)

        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


users_to_feeds = db.Table(
    'users_to_feeds', db.Model.metadata,
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), index=True),
    db.Column('feed_id', db.Integer, db.ForeignKey('feed.id'), index=True))


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(256))
    domain = db.Column(db.String(256))
    micropub_endpoint = db.Column(db.String(512))
    access_token = db.Column(db.String(512))
    settings = db.Column(JsonType)

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
    users = db.relationship(User, secondary='users_to_feeds', backref='feeds')
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
