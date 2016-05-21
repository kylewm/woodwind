Woodwind
========

[![Requirements Status](https://requires.io/github/kylewm/woodwind/requirements.svg?branch=master)](https://requires.io/github/kylewm/woodwind/requirements/?branch=master)

A minimum viable stream-style feed reader.

Supports mf2 h-feed and xml feeds (thanks to Universal Feed Parser).

Installation
----------

How to run your own instance of Woodwind. You'll first need to make
sure you have *Postgres* and *Redis* installed and running.

```bash
git clone https://github.com/kylewm/woodwind.git
cd woodwind
```

Set up the virtualenv and install dependencies.

```bash
virtualenv --python=/usr/bin/python3 venv
source venv/bin/activate
pip install -r requirements.txt
```

Copy woodwind.cfg.template to woodwind.cfg and edit it to check the
Postgres connection string.

Then create database tables and run Woodwind.

```bash
# create the postgres database
createdb woodwind
# copy and edit the configuration file
cp woodwind.cfg.template woodwind.cfg
nano woodwind.cfg
# create the database tables
python init_db.py
# finally run the application
uwsgi woodwind-dev.ini
```

Now visit localhost:3000, and you should see the login screen!
