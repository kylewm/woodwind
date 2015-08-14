Woodwind
========

A minimum viable stream-style feed reader.

Supports mf2 h-feed and xml feeds (thanks to Universal Feed Parser).

Installation
----------

How to run your own instance of Woodwind. The default configuration uses
SQLite, so no database setup is necessary.

```bash
git clone https://github.com/kylewm/woodwind.git
cd woodwind
virtualenv --python=/usr/bin/python3 venv
pip install -r requirements.txt
cp woodwind.cfg.template woodwind.cfg
python init_db.py
uwsgi woodwind-dev.ini
```
