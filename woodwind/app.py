from . import extensions
from .views import views
from .api import api
from .push import push
import flask


def create_app(config_path):
    app = flask.Flask('woodwind')
    app.config.from_pyfile(config_path)
    if not app.debug:
        import logging
        import sys
        app.logger.setLevel(logging.DEBUG)
        app.logger.addHandler(logging.StreamHandler(sys.stdout))
    extensions.init_app(app)
    app.register_blueprint(views)
    app.register_blueprint(api)
    app.register_blueprint(push)
    return app
