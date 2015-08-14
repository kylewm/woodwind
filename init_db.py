#!/usr/bin/env python

from woodwind import create_app
from woodwind.extensions import db

app = create_app()

with app.app_context():
    db.create_all()
