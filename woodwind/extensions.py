from flask.ext.login import LoginManager
from flask.ext.micropub import MicropubClient
from flask.ext.sqlalchemy import SQLAlchemy
from flask_debugtoolbar import DebugToolbarExtension


db = SQLAlchemy()
micropub = MicropubClient(client_id='https://woodwind.xyz/')
login_mgr = LoginManager()
login_mgr.login_view = 'views.index'
#toolbar = DebugToolbarExtension()


def init_app(app):
    db.init_app(app)
    micropub.init_app(app)
    login_mgr.init_app(app)
#    toolbar.init_app(app)
