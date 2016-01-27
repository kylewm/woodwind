Woodwind
========

[![Requirements Status](https://requires.io/github/kylewm/woodwind/requirements.svg?branch=master)](https://requires.io/github/kylewm/woodwind/requirements/?branch=master)

A minimum viable stream-style feed reader.

Supports mf2 h-feed and xml feeds (thanks to Universal Feed Parser).

Installation
----------

How to run your own instance of Woodwind. The default configuration
uses SQLite, so no database setup is necessary.

```bash
git clone https://github.com/kylewm/woodwind.git
cd woodwind
```

Set up the virtualenv and install dependencies.

```bash
virtualenv --python=/usr/bin/python3 venv
pip install -r requirements.txt
```

Use the basic SQLite configuration, create database tables and run Woodwind.

```bash
cp woodwind.cfg.template woodwind.cfg
python init_db.py
uwsgi woodwind-dev.ini
```

Now visit localhost:3000, and you should see the login screen!
