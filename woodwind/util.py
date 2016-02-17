import pickle
import re

from flask import current_app
from redis import StrictRedis
import bleach
import requests

redis = StrictRedis()

bleach.ALLOWED_TAGS += [
    'a', 'img', 'p', 'br', 'marquee', 'blink',
    'audio', 'video', 'source', 'table', 'tbody', 'td', 'tr', 'div', 'span',
    'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
]

bleach.ALLOWED_ATTRIBUTES.update({
    'img': ['src', 'alt', 'title'],
    'audio': ['preload', 'controls', 'src'],
    'video': ['preload', 'controls', 'src', 'poster'],
    'source': ['type', 'src'],
    'td': ['colspan'],
})

USER_AGENT = 'Woodwind (https://github.com/kylewm/woodwind)'


def requests_get(url, **kwargs):
    lastresp = redis.get('resp:' + url)
    if lastresp:
        lastresp = pickle.loads(lastresp)

    headers = kwargs.setdefault('headers', {})
    headers['User-Agent'] = USER_AGENT

    if lastresp:
        if 'Etag' in lastresp.headers:
            headers['If-None-Match'] = lastresp.headers['Etag']
        if 'Last-Modified' in lastresp.headers:
            headers['If-Modified-Since'] = lastresp.headers['Last-Modified']

    current_app.logger.debug('fetching %s with args %s', url, kwargs)
    resp = requests.get(url, **kwargs)

    current_app.logger.debug('fetching %s got response %s', url, resp)
    if resp.status_code == 304:
        return lastresp
    if resp.status_code // 100 == 2:
        redis.setex('resp:' + url, 24 * 3600, pickle.dumps(resp))
    return resp


def clean(text):
    """Strip script tags and other possibly dangerous content
    """
    if text is not None:
        text = re.sub('<script.*?</script>', '', text, flags=re.DOTALL)
        return bleach.clean(text, strip=True)
