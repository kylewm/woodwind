from woodwind import extensions
from woodwind.api import api
from woodwind.push import push
from woodwind.views import views
import flask
import logging
import sys


MAIL_FORMAT = '''\
Message type:       %(levelname)s
Location:           %(pathname)s:%(lineno)d
Module:             %(module)s
Function:           %(funcName)s
Time:               %(asctime)s

Message:

%(message)s
'''


def create_app(config_path='../woodwind.cfg'):
    app = flask.Flask('woodwind')
    app.config.from_pyfile(config_path)
    configure_logging(app)
    extensions.init_app(app)
    app.register_blueprint(views)
    app.register_blueprint(api)
    app.register_blueprint(push)
    return app


def configure_logging(app):
    if app.debug:
        return

    app.logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

    recipients = app.config.get('ADMIN_EMAILS')
    if recipients:
        error_handler = logging.handlers.SMTPHandler(
            'localhost', 'Woodwind <woodwind@kylewm.com>',
            recipients, 'woodwind error')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(MAIL_FORMAT))
        app.logger.addHandler(error_handler)
