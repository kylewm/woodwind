from . import extensions
from .views import views
from .api import api
from .push import push
from config import Config
import flask


def create_app():
    app = flask.Flask('woodwind')
    app.config.from_object(Config)
    extensions.init_app(app)
    app.register_blueprint(views)
    app.register_blueprint(api)
    app.register_blueprint(push)
    return app