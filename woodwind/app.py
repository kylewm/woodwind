from . import extensions
from .views import ui
from config import Config
import flask


def create_app():
    app = flask.Flask('woodwind')
    app.config.from_object(Config)
    extensions.init_app(app)
    app.register_blueprint(ui)
    return app
