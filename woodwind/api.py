import flask
import flask.ext.login as flask_login
import requests
from woodwind import util

api = flask.Blueprint('api', __name__)


@api.route('/publish', methods=['POST'])
def publish():
    action = flask.request.form.get('action')
    target = flask.request.form.get('target')
    content = flask.request.form.get('content')
    syndicate_to = flask.request.form.getlist('syndicate-to[]')

    if syndicate_to:
        syndicate_to = [util.html_unescape(id) for id in syndicate_to]

    data = {
        'h': 'entry',
        'syndicate-to[]': syndicate_to,
        'access_token': flask_login.current_user.access_token,
    }

    if action.startswith('rsvp-'):
        data['in-reply-to'] = target
        data['content'] = content
        data['rsvp'] = action.split('-', 1)[-1]
    elif action == 'like':
        data['like-of'] = target
    elif action == 'repost':
        data['repost-of'] = target
    else:
        data['in-reply-to'] = target
        data['content'] = content

    resp = requests.post(
        flask_login.current_user.micropub_endpoint, data=data, headers={
            'Authorization': 'Bearer {}'.format(
                flask_login.current_user.access_token),
        })

    return flask.jsonify({
        'code': resp.status_code,
        'content': resp.text,
        'content-type': resp.headers.get('content-type'),
        'location': resp.headers.get('location'),
    })


@api.route('/_forward', methods=['GET', 'POST'])
def forward_request():
    if flask.request.method == 'GET':
        args = flask.request.args.copy()
        url = args.pop('_url')
        result = requests.get(url, params=args)
    else:
        data = flask.request.form.copy()
        url = data.pop('_url')
        result = requests.post(url, data=data)

    return flask.jsonify({
        'code': result.status_code,
        'content': result.text,
        'content-type': result.headers.get('content-type'),
        'location': result.headers.get('location'),
    })
