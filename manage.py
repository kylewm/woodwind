#!/usr/bin/env python

from woodwind import create_app
from flask.ext.script import Manager
from flask.ext.migrate import MigrateCommand

app = create_app()
manager = Manager(app)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
