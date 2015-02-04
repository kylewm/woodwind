import flask
import requests

api = flask.Blueprint('api', __name__)


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
