import bleach
from .extensions import db


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
