#!/usr/bin/env python

from distutils.core import setup

setup(name='Woodwind',
      version='1.0.0',
      description='Stream-style indieweb reader',
      author='Kyle Mahan',
      author_email='kyle@kylewm.com',
      url='https://indiewebcamp.com/Woodwind',
      packages=['woodwind'],
      install_requires=[
          'Flask', 'Flask-Login', 'Flask-Micropub', 'Flask-SQLAlchemy',
          'beautifulsoup4', 'bleach', 'celery', 'feedparser', 'html5lib',
          'mf2py', 'mf2util', 'redis', 'requests', 'tornado'])
