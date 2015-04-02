import bleach
import json
import binascii
from .extensions import db
import re
import uuid

from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.ext.associationproxy import association_proxy




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


entry_to_reply_context = db.Table(
    'entry_to_reply_context', db.Model.metadata,
    db.Column('entry_id', db.Integer, db.ForeignKey('entry.id'), index=True),
    db.Column('context_id', db.Integer, db.ForeignKey('entry.id'), index=True))


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

    def get_setting(self, key, default=None):
        if self.settings is None:
            return default
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        if self.settings is None:
            self.settings = {}
        else:
            self.settings = dict(self.settings)
        self.settings[key] = value

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

    push_hub = db.Column(db.String(512))
    push_topic = db.Column(db.String(512))
    push_verified = db.Column(db.Boolean)
    push_expiry = db.Column(db.DateTime)
    push_secret = db.Column(db.String(200))
    last_pinged = db.Column(db.DateTime)

    def get_feed_code(self):
        return binascii.hexlify(self.feed.encode())

    def get_or_create_push_secret(self):
        if not self.push_secret:
            self.push_secret = uuid.uuid4().hex
            db.commit()
        return self.push_secret

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
    content_cleaned = db.Column(db.Text)
    # other properties
    properties = db.Column(JsonType)
    # # association with the InReplyTo objects
    # irt = db.relationship(
    #     'InReplyTo', order_by='InReplyTo.list_index',
    #     collection_class=ordering_list('list_index'))
    # # proxy for just the urls
    # in_reply_to = association_proxy(
    #     'irt', 'url', creator=lambda url: InReplyTo(url=url))
    reply_context = db.relationship(
        'Entry', secondary='entry_to_reply_context',
        primaryjoin=id == entry_to_reply_context.c.entry_id,
        secondaryjoin=id == entry_to_reply_context.c.context_id)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._syndicated_copies = []

    def get_property(self, key, default=None):
        if self.properties is None:
            return default
        return self.properties.get(key, default)

    def set_property(self, key, value):
        self.properties = ({} if self.properties is None
                           else dict(self.properties))
        self.properties[key] = value

    def __repr__(self):
        return '<Entry:{},{}>'.format(self.title, (self.content or '')[:140])


# class InReplyTo(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     entry_id = db.Column(db.Integer, db.ForeignKey(Entry.id))
#     url = db.Column(db.String(512))
#     list_index = db.Column(db.Integer)
